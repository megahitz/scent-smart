"""Program 1 intervals, changed only through verified transactions."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from .const import DOMAIN, RUN_MIN, RUN_MAX, RUN_STEP, SUSPEND_MIN, SUSPEND_MAX, SUSPEND_STEP
from .entity import ScentSmartEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SprayDurationNumber(coordinator, entry), PauseTimeNumber(coordinator, entry)])


class _TimerNumber(ScentSmartEntity, NumberEntity):
    _field = ''

    @property
    def native_value(self):
        state = self.state_obj
        timer = state.programs.get(1) if state else None
        return getattr(timer, self._field) if timer else None

    async def async_set_native_value(self, value):
        await self.coordinator.async_change_timer(self._field, value)


class SprayDurationNumber(_TimerNumber):
    _field = 'run'
    _attr_translation_key = 'spray_duration'
    _attr_native_min_value = RUN_MIN
    _attr_native_max_value = RUN_MAX
    _attr_native_step = RUN_STEP

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, 'spray_duration')


class PauseTimeNumber(_TimerNumber):
    _field = 'suspend'
    _attr_translation_key = 'pause_time'
    _attr_native_min_value = SUSPEND_MIN
    _attr_native_max_value = SUSPEND_MAX
    _attr_native_step = SUSPEND_STEP

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, 'pause_time')
