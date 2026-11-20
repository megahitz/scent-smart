"""On-demand BLE transactions: no boot connection and no polling."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import replace

from bleak import BleakClient, BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import DeviceState, FrameStream, build_frame, op_frame, parse_state, parse_timer_list, timer_frame
from .const import CHARACTERISTIC_UUID

_LOGGER = logging.getLogger(__name__)
CONNECT_TIMEOUT_S = 15.0
ACK_WAIT_S = 5.0


class ScentSmartCoordinator(DataUpdateCoordinator[DeviceState]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, address: str) -> None:
        super().__init__(hass, _LOGGER, name=f'scent_smart_{address}', update_interval=None)
        self.entry = entry
        self.address = address
        self._client = None
        self._lock = asyncio.Lock()
        self._latest = DeviceState()
        self._stream = FrameStream()
        self._waiting = None
        self._expected_cmd = None

    async def _ensure_connected(self):
        device = bluetooth.async_ble_device_from_address(self.hass, self.address, connectable=True)
        if device is None:
            raise UpdateFailed('aparelho não encontrado pelo Bluetooth')
        self._stream = FrameStream()
        self._client = await establish_connection(BleakClient, device, self.address,
                                                  timeout=CONNECT_TIMEOUT_S, max_attempts=1)
        await self._client.start_notify(CHARACTERISTIC_UUID, self._notification_handler)
        return self._client

    async def _disconnect(self):
        client, self._client = self._client, None
        if client is not None:
            try:
                await client.disconnect()
            except (BleakError, OSError):
                _LOGGER.warning('falha ao desconectar %s', self.address)

    @asynccontextmanager
    async def session(self, precondition=None):
        async with self._lock:
            if precondition is not None:
                precondition()
            try:
                await self._ensure_connected()
                yield self._client
            finally:
                self._waiting = self._expected_cmd = None
                await self._disconnect()

    def _notification_handler(self, _char, data):
        for frame in self._stream.feed(bytes(data)):
            if frame[3] != self._expected_cmd or self._waiting is None or self._waiting.done():
                continue
            try:
                result = parse_timer_list(frame) if frame[3] == 0x88 else parse_state(frame)
            except ValueError as err:
                self._waiting.set_exception(UpdateFailed(f'resposta inválida: {err}'))
            else:
                self._waiting.set_result(result)

    async def _request(self, command, response_cmd):
        future = asyncio.get_running_loop().create_future()
        self._expected_cmd, self._waiting = response_cmd, future
        try:
            await self._client.write_gatt_char(CHARACTERISTIC_UUID, command, response=False)
            return await asyncio.wait_for(future, ACK_WAIT_S)
        except asyncio.TimeoutError as err:
            raise UpdateFailed('sem confirmação válida do difusor; resultado desconhecido') from err
        finally:
            self._expected_cmd = self._waiting = None
            if not future.done():
                future.cancel()

    async def _query_timers(self):
        return await self._request(build_frame(0x08, b''), 0x88)

    async def async_change_timer(self, field: str, value: float) -> None:
        bounds = {'run': (5, 200), 'suspend': (20, 300)}
        if field not in bounds or isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('intervalo inválido')
        low, high = bounds[field]
        if not low <= value <= high or value % 5:
            raise ValueError('intervalo fora da faixa ou do passo de 5 segundos')
        async with self.session():
            original = await self._query_timers()
            new_timer = replace(original[1], **{field: int(value)})
            await self._client.write_gatt_char(CHARACTERISTIC_UUID, timer_frame(new_timer), response=False)
            verified = await self._query_timers()
            expected = dict(original)
            expected[1] = new_timer
            if any(verified[i].to_payload() != expected[i].to_payload() for i in range(1, 6)):
                raise UpdateFailed('leitura não confirma todos os bytes; resultado desconhecido')
            state = replace(self._latest, active_serial=1, active_timer=verified[1], programs=verified)
            self._latest = state
            self.async_set_updated_data(state)

    async def async_spray_now(self) -> None:
        """Spray without replacing the stored program.

        When on, re-send the exact validated record. When off, temporarily
        enable and then restore off. Unknown mode is deliberately rejected.
        """
        def require_known_mode():
            if self._latest.running is None:
                raise UpdateFailed('modo automático desconhecido; comando não enviado')

        async with self.session(precondition=require_known_mode):
            running = self._latest.running
            original = await self._query_timers()
            timer = original[1]
            if timer.enable is not True:
                raise UpdateFailed('programa 1 não está habilitado; nenhuma alteração foi enviada')
            if running:
                await self._client.write_gatt_char(CHARACTERISTIC_UUID, timer_frame(timer), response=False)
            else:
                # Attempt OFF in finally even if ON acknowledgement is lost or
                # the operation is cancelled: device may have acted already.
                try:
                    on_state = await self._request(op_frame(0x12, 1), 0x21)
                    if on_state.running is not True:
                        raise UpdateFailed('ligação não confirmada; resultado desconhecido')
                    await asyncio.sleep(timer.run)
                finally:
                    off_state = await self._request(op_frame(0x12, 0), 0x21)
                    if off_state.running is not False:
                        raise UpdateFailed('restauração do modo desligado não confirmada')
                    self._latest = off_state
                    self.async_set_updated_data(off_state)
            verified = await self._query_timers()
            if any(verified[i].to_payload() != original[i].to_payload() for i in range(1, 6)):
                raise UpdateFailed('programas não confirmados; resultado desconhecido')
            state = replace(self._latest, active_serial=1, active_timer=verified[1], programs=verified)
            self._latest = state
            self.async_set_updated_data(state)

    async def async_send_operation(self, func: int, value: int) -> None:
        if func != 0x12 or value not in (0, 1):
            raise UpdateFailed('operação não suportada com confirmação segura')
        async with self.session():
            state = await self._request(op_frame(func, value), 0x21)
            if state.running != bool(value):
                raise UpdateFailed('estado informado não confirma o comando; resultado desconhecido')
            if self._latest.programs:
                state.programs = self._latest.programs
            self._latest = state
            self.async_set_updated_data(state)

    async def async_shutdown_connection(self) -> None:
        async with self._lock:
            await self._disconnect()

    async def _async_update_data(self) -> DeviceState:
        return self._latest
