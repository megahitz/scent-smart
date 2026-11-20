"""Legacy ambient light remains unavailable without confirmed state."""
from homeassistant.components.light import ColorMode, LightEntity
from .const import DOMAIN
from .entity import ScentSmartEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ScentSmartAmbientLight(hass.data[DOMAIN][entry.entry_id], entry, 'ambient_light')])


class ScentSmartAmbientLight(ScentSmartEntity, LightEntity):
    _attr_translation_key = 'ambient_light'
    _attr_supported_color_modes = {ColorMode.ONOFF}

    @property
    def available(self):
        return False

    @property
    def is_on(self):
        return None

    async def async_turn_on(self, **kwargs):
        raise RuntimeError('Luz indisponível sem confirmação de estado')

    async def async_turn_off(self, **kwargs):
        raise RuntimeError('Luz indisponível sem confirmação de estado')
