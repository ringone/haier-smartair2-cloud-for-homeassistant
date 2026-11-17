"""Offline configuration for direct SmartAir2 LAN connections."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback

from .const import CONF_LOCAL_IPS, DOMAIN
from .local_map import format_local_map, parse_local_map


def _validate_input(user_input: dict[str, Any]) -> dict[str, str]:
    return {CONF_LOCAL_IPS: format_local_map(parse_local_map(user_input.get(CONF_LOCAL_IPS)))}


class HaierConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure local devices without contacting them or a remote service."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HaierOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                data = _validate_input(user_input)
            except ValueError:
                errors[CONF_LOCAL_IPS] = "invalid_local_map"
            else:
                return self.async_create_entry(title="Haier SmartAir2 (local)", data=data)
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({vol.Required(CONF_LOCAL_IPS): str}), errors=errors
        )


class HaierOptionsFlow(OptionsFlow):
    """Recover old cloud-only entries by configuring their local map."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                data = _validate_input(user_input)
            except ValueError:
                errors[CONF_LOCAL_IPS] = "invalid_local_map"
            else:
                return self.async_create_entry(title="", data=data)
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_LOCAL_IPS, default=current.get(CONF_LOCAL_IPS, "")): str}),
            errors=errors,
        )
