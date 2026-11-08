"""UI configuration for A-OK RS485 motors via USR-DR164 TCP bridge."""
from __future__ import annotations

import asyncio

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import callback

from .const import (
    DOMAIN, CONF_CHANNEL, CONF_DEVICE_ID, CONF_TIMEOUT, CONF_POLL_INTERVAL, CONF_POLL_STATUS, DEFAULT_POLL_STATUS,
    DEFAULT_NAME, DEFAULT_HOST, DEFAULT_PORT, DEFAULT_TIMEOUT, DEFAULT_POLL_INTERVAL,
)


def form_schema(values: dict | None = None) -> vol.Schema:
    """Construct defaults for the connection and polling options."""
    values = values or {}
    return vol.Schema({
        vol.Required(CONF_NAME, default=values.get(CONF_NAME, DEFAULT_NAME)): str,
        vol.Required(CONF_HOST, default=values.get(CONF_HOST, DEFAULT_HOST)): str,
        vol.Required(CONF_PORT, default=values.get(CONF_PORT, DEFAULT_PORT)):
            vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required(CONF_DEVICE_ID, default=values.get(CONF_DEVICE_ID, 1)):
            vol.All(vol.Coerce(int), vol.Range(min=1, max=99)),
        vol.Required(CONF_CHANNEL, default=values.get(CONF_CHANNEL, 1)):
            vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
        vol.Required(CONF_TIMEOUT, default=values.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)):
            vol.All(vol.Coerce(float), vol.Range(min=0.5, max=30)),
        vol.Required(CONF_POLL_STATUS, default=values.get(CONF_POLL_STATUS, DEFAULT_POLL_STATUS)): bool,
        vol.Required(CONF_POLL_INTERVAL, default=values.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)):
            vol.All(vol.Coerce(int), vol.Range(min=5, max=3600)),
    })


async def test_connection(host: str, port: int, timeout: float) -> None:
    """Verify gateway TCP reachability, not motor RS485 response."""
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port), timeout=timeout
    )
    del reader
    writer.close()
    await writer.wait_closed()


class AokRS485ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Set up A-OK curtain through a UI form."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            if not user_input[CONF_HOST]:
                errors[CONF_HOST] = "invalid_host"
            else:
                try:
                    await test_connection(
                        user_input[CONF_HOST], user_input[CONF_PORT], user_input[CONF_TIMEOUT]
                    )
                except (OSError, asyncio.TimeoutError):
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(
                        f"{user_input[CONF_HOST].lower()}:{user_input[CONF_PORT]}:"
                        f"{user_input[CONF_DEVICE_ID]}:{user_input[CONF_CHANNEL]}"
                    )
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=form_schema(user_input), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return AokRS485OptionsFlow()


class AokRS485OptionsFlow(config_entries.OptionsFlow):
    """Change connection and polling settings from integration options."""
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            if not user_input[CONF_HOST]:
                errors[CONF_HOST] = "invalid_host"
            else:
                try:
                    await test_connection(
                        user_input[CONF_HOST], user_input[CONF_PORT], user_input[CONF_TIMEOUT]
                    )
                except (OSError, asyncio.TimeoutError):
                    errors["base"] = "cannot_connect"
                else:
                    # Keep the entry's original unique_id. Changing the ID/channel
                    # is an explicit reconfiguration of this same cover entity.
                    return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=form_schema(user_input or {**self.config_entry.data, **self.config_entry.options}),
            errors=errors,
        )
