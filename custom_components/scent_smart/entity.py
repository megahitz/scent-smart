"""Shared entity helpers for the Scent Smart integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DOMAIN, MANUFACTURER, MODEL
from .coordinator import ScentSmartCoordinator


ENTITY_NAMES = {
    "working_mode": "Modo de Trabalho",
    "fan": "Ventilador",
    "child_lock": "Trava Infantil",
    "spray_now": "Borrifar Agora",
    "spray_duration": "Tempo de Borrifada",
    "pause_time": "Tempo de Pausa",
    "active_program": "Programa Ativo",
    "state": "Estado",
    "ambient_light": "Luz Ambiente",
}

# Interface enxuta: só o essencial fica habilitado por padrão.
HIDDEN_KEYS = {"fan", "child_lock", "ambient_light", "active_program"}


class ScentSmartEntity(CoordinatorEntity[ScentSmartCoordinator]):
    """Base for all Scent Smart entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ScentSmartCoordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._key = key
        self._attr_name = ENTITY_NAMES.get(key, key)
        self._attr_entity_registry_enabled_default = key not in HIDDEN_KEYS and not key.startswith("program_")

    @property
    def device_info(self) -> DeviceInfo:
        address = self.coordinator.address
        name = self._entry.data.get(CONF_NAME) or "Scent Diffuser"
        return DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def state_obj(self):
        return self.coordinator.data

    @property
    def active_serial(self) -> int:
        st = self.state_obj
        if st and st.active_serial:
            return st.active_serial
        return int(self._entry.options.get("active_program", 1))
