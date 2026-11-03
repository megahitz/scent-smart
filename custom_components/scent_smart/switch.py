"""Switch platform: working mode, fan, child lock, per-program enable."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import TimerState
from .const import (
    CONF_DEFAULT_PAUSE_TIME,
    CONF_DEFAULT_SPRAY_DURATION,
    CONF_DEFAULT_WINDOW_START,
    CONF_DEFAULT_WINDOW_STOP,
    DEFAULT_PAUSE_TIME,
    DEFAULT_SPRAY_DURATION,
    DEFAULT_WINDOW_START,
    DEFAULT_WINDOW_STOP,
    DOMAIN,
    FUNC_CHILD_LOCK,
    FUNC_FAN,
    FUNC_RUNNING_STATUS,
    NUM_PROGRAMS,
    TIMER_MODE_EVERY_DAY,
)
from .entity import ScentSmartEntity

_toggle_funcs = {"working_mode": FUNC_RUNNING_STATUS, "fan": FUNC_FAN, "child_lock": FUNC_CHILD_LOCK}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [ScentSmartToggle(coordinator, entry, key, func) for key, func in _toggle_funcs.items()]
    entities += [
        ScentSmartProgramSwitch(coordinator, entry, serial) for serial in range(1, NUM_PROGRAMS + 1)
    ]
    async_add_entities(entities)


class ScentSmartToggle(ScentSmartEntity, SwitchEntity):
    """switch.scent_smart_working_mode / _fan / _child_lock via CMD 0x07."""

    def __init__(self, coordinator, entry, key: str, func: int) -> None:
        super().__init__(coordinator, entry, key)
        self._func = func
        self._attr_translation_key = key
        self._optimistic: bool | None = None

    @property
    def is_on(self) -> bool | None:
        if self._optimistic is not None:
            return self._optimistic
        st = self.state_obj
        if not st:
            return None
        mapping = {
            FUNC_RUNNING_STATUS: st.running,
            FUNC_FAN: st.fan,
            FUNC_CHILD_LOCK: st.child_lock,
        }
        return mapping.get(self._func)

    async def async_turn_on(self, **kwargs) -> None:
        await self._send(1)

    async def async_turn_off(self, **kwargs) -> None:
        await self._send(0)

    async def _send(self, value: int) -> None:
        self._optimistic = bool(value)
        self.async_write_ha_state()
        await self.coordinator.async_send_operation(self._func, value)
        await self.coordinator.async_wait_state()
        self._optimistic = None
        self.async_write_ha_state()


class ScentSmartProgramSwitch(ScentSmartEntity, SwitchEntity):
    """switch.scent_smart_program_N_enabled: CMD 0x14 enable flag for serial N."""

    def __init__(self, coordinator, entry, serial: int) -> None:
        super().__init__(coordinator, entry, f"program_{serial}_enabled")
        self._serial = serial
        self._attr_name = f"Programa {serial}"

    @property
    def is_on(self) -> bool | None:
        st = self.state_obj
        if not st or self._serial not in st.programs:
            return None
        return st.programs[self._serial].enable

    async def async_turn_on(self, **kwargs) -> None:
        await self._set_enable(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set_enable(False)

    async def _set_enable(self, enable: bool) -> None:
        st = self.state_obj
        existing = st.programs.get(self._serial) if st else None
        opts = self._entry.options
        timer = TimerState(
            enable=enable,
            serial=self._serial,
            mode=existing.mode if existing else TIMER_MODE_EVERY_DAY,
            start=existing.start if existing else int(opts.get(CONF_DEFAULT_WINDOW_START, DEFAULT_WINDOW_START)),
            stop=existing.stop if existing else int(opts.get(CONF_DEFAULT_WINDOW_STOP, DEFAULT_WINDOW_STOP)),
            run=existing.run if existing else int(opts.get(CONF_DEFAULT_SPRAY_DURATION, DEFAULT_SPRAY_DURATION)),
            suspend=(
                existing.suspend
                if existing
                else int(opts.get(CONF_DEFAULT_PAUSE_TIME, DEFAULT_PAUSE_TIME))
            ),
        )
        await self.coordinator.async_send_timer(timer)
        await self.coordinator.async_wait_state()
