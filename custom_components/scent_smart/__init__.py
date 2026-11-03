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
    # Conexão imediata em background: sincroniza o estado assim que o
    # aparelho aparecer no scan, sem bloquear o setup do HA.
    boot_task = hass.async_create_background_task(
        coordinator.async_boot_connect(), "scent_smart_boot_connect"
    )
    entry.async_on_unload(lambda: boot_task.cancel())
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_options_listener))
    return True


async def _options_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Options (defaults) are read by entities at runtime; nothing cached.
    return


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: ScentSmartCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown_connection()
    return unload_ok
