"""Initial BLE address and name only; no schedule/default editor."""
from __future__ import annotations
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from .const import CONF_BLE_ADDRESS, CONF_NAME, DOMAIN

_MAC_CHARS = set('0123456789ABCDEF')


def _validate_address(address: str) -> str:
    address = address.strip().upper().replace('-', ':')
    parts = address.split(':')
    if len(parts) != 6 or not all(len(p) == 2 and set(p) <= _MAC_CHARS for p in parts):
        raise vol.Invalid('invalid_ble_address')
    return address


class ScentSmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors = {}
        if user_input is not None:
            try:
                address = _validate_address(user_input[CONF_BLE_ADDRESS])
            except vol.Invalid:
                errors[CONF_BLE_ADDRESS] = 'invalid_ble_address'
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input.get(CONF_NAME) or 'Scent Diffuser',
                    data={CONF_BLE_ADDRESS: address, CONF_NAME: user_input.get(CONF_NAME, '')})
        schema = vol.Schema({vol.Required(CONF_BLE_ADDRESS): str,
                             vol.Optional(CONF_NAME, default='Scent Diffuser'): str})
        return self.async_show_form(step_id='user', data_schema=schema, errors=errors)
