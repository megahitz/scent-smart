"""Select platform: active program (1..5)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, NUM_PROGRAMS
from .entity import ScentSmartEntity

OPTIONS = [f"program_{i}" for i in range(1, NUM_PROGRAMS + 1)]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ScentSmartActiveProgram(coordinator, entry, "active_program")])


class ScentSmartActiveProgram(ScentSmartEntity, SelectEntity):
    """select.scent_smart_active_program — chooses which program the numbers write."""

    _attr_translation_key = "active_program"
    _attr_options = OPTIONS

    async def async_select_option(self, option: str) -> None:
        serial = int(option.rsplit("_", 1)[1])
        # Persist selection in entry options so it survives restarts.
        new_options = dict(self._entry.options)
        new_options["active_program"] = serial
        self.hass.async_create_task(
            self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        )
        self.async_write_ha_state()

    @property
    def current_option(self) -> str | None:
        st = self.state_obj
        serial = None
        if st and st.active_serial:
            serial = st.active_serial
        else:
            serial = int(self._entry.options.get("active_program", 1))
        return f"program_{serial}"

    @property
    def active_serial(self) -> int:
        """For this entity, the user's manual selection wins over the dump."""
        st = self.state_obj
        if st and st.active_serial:
            return st.active_serial
        return int(self._entry.options.get("active_program", 1))
