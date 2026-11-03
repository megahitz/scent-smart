"""Config and options flows for Scent Smart."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_BLE_ADDRESS,
    CONF_DEFAULT_PAUSE_TIME,
    CONF_DEFAULT_SPRAY_DURATION,
    CONF_DEFAULT_WINDOW_START,
    CONF_DEFAULT_WINDOW_STOP,
    CONF_NAME,
    CONF_ONESHOT_SPRAY_DURATION,
    DEFAULT_PAUSE_TIME,
    DEFAULT_SPRAY_DURATION,
    DEFAULT_WINDOW_START,
    DEFAULT_WINDOW_STOP,
    DOMAIN,
    NUM_PROGRAMS,
    RUN_MAX,
    RUN_MIN,
    SUSPEND_MAX,
    SUSPEND_MIN,
)

_MAC_CHARS = set("0123456789ABCDEFabcdef")


def _validate_address(address: str) -> str:
    address = address.strip().upper().replace("-", ":")
    parts = address.split(":")
    if len(parts) != 6 or any(len(p) != 2 and set(p) <= _MAC_CHARS for p in parts) or not all(
        len(p) == 2 and set(p) <= _MAC_CHARS for p in parts
    ):
        raise vol.Invalid("invalid_ble_address")
    return address


def _time_minute(value: Any) -> int:
    """Accept 'HH:MM' or minutes."""
    if isinstance(value, str) and ":" in value:
        h, m = value.split(":", 1)
        return int(h) * 60 + int(m)
    return int(value)


class ScentSmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """User flow: BLE address + friendly name."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                address = _validate_address(user_input[CONF_BLE_ADDRESS])
            except vol.Invalid:
                errors[CONF_BLE_ADDRESS] = "invalid_ble_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME) or "Scent Diffuser",
                    data={CONF_BLE_ADDRESS: address, CONF_NAME: user_input.get(CONF_NAME, "")},
                )
        schema = vol.Schema(
            {
                vol.Required(CONF_BLE_ADDRESS, default="54:6C:50:5E:C3:6F"): str,
                vol.Optional(CONF_NAME, default="Scent Diffuser"): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ScentSmartOptionsFlow:
        return ScentSmartOptionsFlow(config_entry)


class ScentSmartOptionsFlow(config_entries.OptionsFlow):
    """Options: defaults, program selection, one-shot spray duration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        opts = self._entry.options
        if user_input is not None:
            try:
                user_input = {
                    **user_input,
                    CONF_DEFAULT_WINDOW_START: _time_minute(user_input[CONF_DEFAULT_WINDOW_START]),
                    CONF_DEFAULT_WINDOW_STOP: _time_minute(user_input[CONF_DEFAULT_WINDOW_STOP]),
                }
                return self.async_create_entry(title="", data=user_input)
            except (ValueError, vol.Invalid):
                errors["base"] = "invalid_time"
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEFAULT_SPRAY_DURATION,
                    default=opts.get(CONF_DEFAULT_SPRAY_DURATION, DEFAULT_SPRAY_DURATION),
                ): vol.All(vol.Coerce(int), vol.Range(min=RUN_MIN, max=RUN_MAX, step=RUN_STEP)),
                vol.Required(
                    CONF_DEFAULT_PAUSE_TIME,
                    default=opts.get(CONF_DEFAULT_PAUSE_TIME, DEFAULT_PAUSE_TIME),
                ): vol.All(vol.Coerce(int), vol.Range(min=SUSPEND_MIN, max=SUSPEND_MAX, step=SUSPEND_STEP)),
                vol.Required(
                    CONF_DEFAULT_WINDOW_START,
                    default=self._fmt(opts.get(CONF_DEFAULT_WINDOW_START, DEFAULT_WINDOW_START)),
                ): str,
                vol.Required(
                    CONF_DEFAULT_WINDOW_STOP,
                    default=self._fmt(opts.get(CONF_DEFAULT_WINDOW_STOP, DEFAULT_WINDOW_STOP)),
                ): str,
                vol.Required(
                    "active_program",
                    default=opts.get("active_program", 1),
                ): vol.All(vol.Coerce(int), vol.In(range(1, NUM_PROGRAMS + 1))),
                vol.Required(
                    CONF_ONESHOT_SPRAY_DURATION,
                    default=opts.get(CONF_ONESHOT_SPRAY_DURATION, 15),
                ): vol.All(vol.Coerce(int), vol.Range(min=RUN_MIN, max=RUN_MAX, step=RUN_STEP)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    @staticmethod
    def _fmt(minutes: int) -> str:
        return f"{minutes // 60:02d}:{minutes % 60:02d}"
