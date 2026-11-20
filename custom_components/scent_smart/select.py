"""Legacy program selector retained as unavailable; numbers use program 1."""
from homeassistant.components.select import SelectEntity
from .const import DOMAIN, NUM_PROGRAMS
from .entity import ScentSmartEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ScentSmartActiveProgram(hass.data[DOMAIN][entry.entry_id], entry, 'active_program')])


class ScentSmartActiveProgram(ScentSmartEntity, SelectEntity):
    _attr_translation_key = 'active_program'
    _attr_options = [f'program_{i}' for i in range(1, NUM_PROGRAMS + 1)]

    @property
    def available(self):
        return False

    @property
    def current_option(self):
        return None

    async def async_select_option(self, option):
        raise RuntimeError('Seleção de programa indisponível; intervalos usam o programa 1')
