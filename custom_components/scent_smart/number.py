"""Number platform: spray duration and pause time of the ACTIVE program."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .client import TimerState
from .const import (
    RUN_MAX,
    RUN_MIN,
    RUN_STEP,
    SUSPEND_MAX,
    SUSPEND_MIN,
    SUSPEND_STEP,
    DOMAIN,
)
from .entity import ScentSmartEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SprayDurationNumber(coordinator, entry),
            PauseTimeNumber(coordinator, entry),
        ]
    )


class _TimerNumber(ScentSmartEntity, NumberEntity):
    """Writes CMD 0x14 rebuilding the ACTIVE program's timer frame."""

    def _current(self) -> int | None:
        st = self.state_obj
        if not st or not st.active_timer:
            return None
        return self._get(st.active_timer)

    async def _write(self, value: float) -> None:
        st = self.state_obj
        timer: TimerState
        if st and st.active_timer:
            timer = TimerState(**vars(st.active_timer))
        else:
            from .const import (
                DEFAULT_PAUSE_TIME,
                DEFAULT_SPRAY_DURATION,
                DEFAULT_WINDOW_START,
                DEFAULT_WINDOW_STOP,
                TIMER_MODE_EVERY_DAY,
            )
            opts = self._entry.options
            timer = TimerState(
                serial=self.active_serial, mode=TIMER_MODE_EVERY_DAY,
                start=int(opts.get("default_window_start", DEFAULT_WINDOW_START)),
                stop=int(opts.get("default_window_stop", DEFAULT_WINDOW_STOP)),
                run=int(opts.get("default_spray_duration", DEFAULT_SPRAY_DURATION)),
                suspend=int(opts.get("default_pause_time", DEFAULT_PAUSE_TIME)),
            )
        timer = TimerState(
            enable=timer.enable, serial=timer.serial, mode=timer.mode,
            start=timer.start, stop=timer.stop, suspend=timer.suspend,
            run=timer.run,
        )
        self._set(timer, int(value))
        await self.coordinator.async_send_timer(timer)
        await self.coordinator.async_wait_state()
        # Persistir o valor nas opções: é a config que o boot reaplica.
        opts = dict(self._entry.options)
        opts[self._options_key()] = int(value)
        self.hass.config_entries.async_update_entry(self._entry, options=opts)

    def _options_key(self) -> str:  # pragma: no cover - overridden
        return "default_spray_duration"

    def _get(self, timer: TimerState) -> int:  # pragma: no cover - overridden
        return timer.run

    def _set(self, timer: TimerState, value: int) -> None:  # pragma: no cover
        timer.run = value


class SprayDurationNumber(_TimerNumber):
    _attr_translation_key = "spray_duration"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "spray_duration")
        self._attr_native_min_value = RUN_MIN
        self._attr_native_max_value = RUN_MAX
        self._attr_native_step = RUN_STEP

    @property
    def native_value(self) -> float | None:
        return self._current()

    async def async_set_native_value(self, value: float) -> None:
        await self._write(value)

    def _set(self, timer: TimerState, value: int) -> None:
        timer.run = value


class PauseTimeNumber(_TimerNumber):
    _attr_translation_key = "pause_time"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "pause_time")
        self._attr_native_min_value = SUSPEND_MIN
        self._attr_native_max_value = SUSPEND_MAX
        self._attr_native_step = SUSPEND_STEP

    def _options_key(self) -> str:
        return "default_pause_time"

    @property
    def native_value(self) -> float | None:
        return self._current()

    async def async_set_native_value(self, value: float) -> None:
        await self._write(value)

    def _get(self, timer: TimerState) -> int:
        return timer.suspend

    def _set(self, timer: TimerState, value: int) -> None:
        timer.suspend = value
