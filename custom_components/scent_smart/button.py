"""Button platform: one-shot spray with restore — all in a single BLE session."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import TimerState, timer_frame
from .const import CHARACTERISTIC_UUID, CONF_ONESHOT_SPRAY_DURATION, DOMAIN, MIN_SPRAY_GUARD_SECONDS
from .entity import ScentSmartEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScentSmartSprayNow(coordinator, entry)])


class ScentSmartSprayNow(ScentSmartEntity, ButtonEntity):
    """Borrifada única: escreve run=X, espera, restaura — numa única conexão."""

    _attr_translation_key = "spray_now"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "spray_now")
        self._busy = False

    async def async_press(self) -> None:
        if self._busy:
            _LOGGER.debug("%s: spray already in progress", self.coordinator.address)
            return
        self._busy = True
        try:
            spray_run = int(self._entry.options.get(CONF_ONESHOT_SPRAY_DURATION, 15))
            async with self.coordinator.session():
                client = self.coordinator._client
                # Com a conexão aberta o aparelho empurra o dump de estado.
                got = await self.coordinator.async_wait_state(timeout=8.0)
                timer = got.active_timer if got else None
                if timer is None:
                    raise RuntimeError(
                        "sem estado do difusor; borrifada cancelada para não sobrescrever o timer"
                    )
                original = TimerState(**vars(timer))
                one_shot = TimerState(
                    enable=timer.enable, serial=timer.serial, mode=timer.mode,
                    start=timer.start, stop=timer.stop,
                    run=spray_run, suspend=timer.suspend,
                )
                await client.write_gatt_char(
                    CHARACTERISTIC_UUID, timer_frame(one_shot), response=False
                )
                await self.coordinator.async_wait_state()
                # Espera a borrifada terminar (+ guarda mínima de 3s).
                await asyncio.sleep(max(spray_run + 1, MIN_SPRAY_GUARD_SECONDS))
                # O aparelho NÃO restaura sozinho: gravar o ciclo original de volta.
                await client.write_gatt_char(
                    CHARACTERISTIC_UUID, timer_frame(original), response=False
                )
                await self.coordinator.async_wait_state()
        finally:
            self._busy = False
