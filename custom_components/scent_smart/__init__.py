"""The Scent Smart integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ScentSmartCoordinator

PLATFORMS = [
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.LIGHT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    coordinator = ScentSmartCoordinator(hass, entry, entry.data["ble_address"])
    hass.data[DOMAIN][entry.entry_id] = coordinator
    # Setup is intentionally passive; only explicit actions open a BLE session.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: ScentSmartCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown_connection()
    return unload_ok
