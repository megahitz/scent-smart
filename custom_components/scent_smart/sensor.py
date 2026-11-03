"""Sensor platform: friendly state + full diagnostic attributes."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import ScentSmartEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScentSmartStateSensor(coordinator, entry, "state")])


class ScentSmartStateSensor(ScentSmartEntity, SensorEntity):
    """sensor.scent_smart_state — Running/Idle/Off with timer + raw dump attributes."""

    _attr_translation_key = "state"

    @property
    def native_value(self) -> str | None:
        st = self.state_obj
        if not st:
            return None
        running = st.running
        timer = st.active_timer
        if running is True:
            return "Running"
        if running is False and timer is not None and timer.enable:
            return "Idle"
        return "Off"

    @property
    def extra_state_attributes(self) -> dict | None:
        st = self.state_obj
        if not st:
            return None
        return st.as_dict()
