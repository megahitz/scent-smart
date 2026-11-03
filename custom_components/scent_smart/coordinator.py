"""Coordinator: conexão SOB DEMANDA (conecta → age → desconecta).

Modelo escolhido pelo usuário: o aparelho BIPA a cada tentativa de conexão,
então a integração NÃO mantém link persistente nem faz polling. Conecta-se
apenas em: boot (aplica a config), mudança de configuração e comandos
(ligar/desligar modo automático, borrifar, ajustar tempos).
"""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager

from bleak import BleakClient, BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import DeviceState, TimerState, op_frame, parse_state, split_notify, timer_frame
from .const import CHARACTERISTIC_UUID

_LOGGER = logging.getLogger(__name__)

BOOT_MAX_ATTEMPTS = 8          # tentativas no boot
BOOT_BACKOFF_S = 45            # espera entre tentativas de boot
CONNECT_TIMEOUT_S = 15.0
ACK_WAIT_S = 5.0


class ScentSmartCoordinator(DataUpdateCoordinator[DeviceState]):
    """Sem polling: cada comando abre a própria conexão e fecha ao final."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, address: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"scent_smart_{address}",
            update_interval=None,  # sem polling — conexão só sob demanda
        )
        self.entry = entry
        self.address = address
        self._client: BleakClient | None = None
        self._lock = asyncio.Lock()
        self._latest = DeviceState()

    # ------------------------------------------------------------------ conexão

    async def _ensure_connected(self) -> BleakClient:
        client = self._client
        if client is not None and client.is_connected:
            return client
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            raise UpdateFailed("aparelho não visto pelo rádio Bluetooth do HA")
        client = await establish_connection(
            BleakClient, device, self.address, timeout=CONNECT_TIMEOUT_S
        )
        self._client = client
        await client.start_notify(CHARACTERISTIC_UUID, self._notification_handler)
        # O aparelho NÃO empurra estado espontaneamente: pedir sync (func 0x01),
        # exatamente como o app oficial faz ao conectar.
        try:
            await client.write_gatt_char(
                CHARACTERISTIC_UUID, op_frame(0x01, 0), response=False
            )
        except (BleakError, asyncio.TimeoutError, OSError) as err:
            _LOGGER.warning("%s: sync request inicial falhou (%s)", self.address, err)
        _LOGGER.info("%s: conectado ao difusor", self.address)
        return client

    async def _disconnect(self) -> None:
        if self._client is not None:
            try:
                await self._client.disconnect()
            except BleakError:
                pass
            self._client = None
        _LOGGER.info("%s: conexão encerrada", self.address)

    @asynccontextmanager
    async def session(self):
        """Ciclo completo: conecta, executa o bloco, desconecta."""
        async with self._lock:
            try:
                await self._ensure_connected()
                yield self._client
            finally:
                await self._disconnect()

    def _notification_handler(self, _char, data: bytearray) -> None:
        try:
            frames = split_notify(bytes(data))
        except Exception:
            _LOGGER.exception("%s: erro no split de notificação", self.address)
            return
        for frame in frames:
            try:
                parsed = parse_state(frame)
            except Exception:
                _LOGGER.exception("%s: erro ao parsear frame %s", self.address, frame.hex())
                continue
            if parsed.active_timer or parsed.running is not None or parsed.unknown:
                self._latest = parsed
                self.async_set_updated_data(parsed)

    # ------------------------------------------------------------------ comandos

    async def async_wait_state(self, timeout: float = ACK_WAIT_S) -> DeviceState | None:
        """Espera um frame novo (dump de estado ou ACK) chegar."""
        deadline = time.monotonic() + timeout
        seen = self._latest
        while time.monotonic() < deadline:
            await asyncio.sleep(0.5)
            if self._latest is not seen and (self._latest.active_timer or self._latest.unknown):
                return self._latest
        return None

    async def async_send_operation(self, func: int, value: int) -> None:
        """Comando CMD 0x07 com ciclo completo de conexão."""
        async with self.session():
            await self._client.write_gatt_char(
                CHARACTERISTIC_UUID, op_frame(func, value), response=False
            )
            await self.async_wait_state()

    async def async_send_timer(self, timer: TimerState) -> None:
        """Comando CMD 0x14 com ciclo completo de conexão."""
        async with self.session():
            await self._client.write_gatt_char(
                CHARACTERISTIC_UUID, timer_frame(timer), response=False
            )
            await self.async_wait_state()

    async def async_shutdown_connection(self) -> None:
        async with self._lock:
            await self._disconnect()

    # ------------------------------------------------------------------ boot

    async def async_boot_connect(self) -> None:
        """No boot: conecta, lê o estado, aplica a config salva e desconecta.

        O HA é a fonte da verdade: os valores configurados (Tempo de Borrifada
        e Tempo de Pausa) são gravados no programa ativo preservando janela,
        dias e habilitação lidos do aparelho.
        """
        opts = self.entry.options
        target_run = int(opts.get("default_spray_duration", 15))
        target_suspend = int(opts.get("default_pause_time", 200))
        for attempt in range(BOOT_MAX_ATTEMPTS):
            if attempt:
                await asyncio.sleep(BOOT_BACKOFF_S)
            try:
                async with self.session():
                    got = await self.async_wait_state(timeout=8.0)
                    timer = got.active_timer if got else None
                    if timer is None:
                        _LOGGER.info("%s: sem dump no boot; aplicando defaults", self.address)
                        from .const import (  # noqa: PLC0415
                            DEFAULT_WINDOW_START,
                            DEFAULT_WINDOW_STOP,
                            TIMER_MODE_EVERY_DAY,
                        )
                        timer = TimerState(
                            serial=1, mode=TIMER_MODE_EVERY_DAY,
                            start=DEFAULT_WINDOW_START, stop=DEFAULT_WINDOW_STOP,
                            run=target_run, suspend=target_suspend,
                        )
                    apply_timer = TimerState(
                        enable=timer.enable, serial=timer.serial, mode=timer.mode,
                        start=timer.start, stop=timer.stop,
                        run=target_run, suspend=target_suspend,
                    )
                    if apply_timer.run != timer.run or apply_timer.suspend != timer.suspend:
                        await self._client.write_gatt_char(
                            CHARACTERISTIC_UUID, timer_frame(apply_timer), response=False
                        )
                        await self.async_wait_state()
                        _LOGGER.info(
                            "%s: config aplicada no boot (run=%ds suspend=%ds)",
                            self.address, target_run, target_suspend,
                        )
                    else:
                        _LOGGER.info("%s: aparelho já está com a config salva", self.address)
                return
            except (BleakError, asyncio.TimeoutError, OSError, UpdateFailed) as err:
                _LOGGER.info("%s: boot connect falhou (%s)", self.address, err)
        _LOGGER.warning("%s: desistindo do boot connect por agora", self.address)

    # ------------------------------------------------------------------ compat

    async def _async_update_data(self) -> DeviceState:
        """Sem polling: retorna o último estado conhecido."""
        return self._latest
