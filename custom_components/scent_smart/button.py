"""Reapply the confirmed program for an on-demand spray."""
from homeassistant.components.button import ButtonEntity
from .const import DOMAIN
from .entity import ScentSmartEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ScentSmartSprayNow(hass.data[DOMAIN][entry.entry_id], entry)])


class ScentSmartSprayNow(ScentSmartEntity, ButtonEntity):
    _attr_translation_key = 'spray_now'

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, 'spray_now')

    async def async_press(self):
        await self.coordinator.async_spray_now()
