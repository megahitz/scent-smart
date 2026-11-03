"""Light platform: ambient light (0=off, 1=on, 2=mode)."""
from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, FUNC_AMBIENT_LIGHT
from .entity import ScentSmartEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScentSmartAmbientLight(coordinator, entry, "ambient_light")])


class ScentSmartAmbientLight(ScentSmartEntity, LightEntity):
    """light.scent_smart_ambient_light via CMD 0x07 func 0x15."""

    _attr_translation_key = "ambient_light"
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _optimistic: bool | None = None

    @property
    def is_on(self) -> bool | None:
        if self._optimistic is not None:
            return self._optimistic
        st = self.state_obj
        if not st or st.ambient_light is None:
            return None
        return st.ambient_light >= 1

    async def async_turn_on(self, **kwargs) -> None:
        await self._send(1)

    async def async_turn_off(self, **kwargs) -> None:
        await self._send(0)

    async def _send(self, value: int) -> None:
        self._optimistic = bool(value)
        self.async_write_ha_state()
        await self.coordinator.async_send_operation(FUNC_AMBIENT_LIGHT, value)
        await self.coordinator.async_wait_state()
        self._optimistic = None
        self.async_write_ha_state()
