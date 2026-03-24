"""Config flow for Vents Breezy integration."""
from __future__ import annotations

import logging
from typing import Any

from vents_breezy import Fan
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS, default="<broadcast>"): str,
        vol.Optional(CONF_PORT, default=4000): int,
        vol.Optional(CONF_DEVICE_ID, default="DEFAULT_DEVICEID"): str,
        vol.Required(CONF_PASSWORD, default="1111"): str,
        vol.Optional(CONF_NAME, default="Vento Expert Fan"): str,
    }
)


class VentoHub:
    """Vento Hub Class."""

    def __init__(self, host: str, port: int, fan_id: str, name: str) -> None:
        """Initialize."""
        self.host = host
        self.port = port
        self.fan_id = fan_id
        self.fan = None
        self.name = name

    async def authenticate(self, password: str) -> bool:
        """Authenticate."""
        self.fan = Fan(self.host, password, self.fan_id, self.name, self.port)
        self.fan.init_device()
        self.fan_id = self.fan.id
        self.name = self.name + " " + self.fan_id
        return self.fan.id != "DEFAULT_DEVICEID"


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    hub = VentoHub(
        data[CONF_IP_ADDRESS], data[CONF_PORT], data[CONF_DEVICE_ID], data[CONF_NAME]
    )

    if not await hub.authenticate(data[CONF_PASSWORD]):
        raise InvalidAuth

    return {"title": hub.name, "id": hub.fan_id}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vents Breezy."""

    VERSION = 2

    def __init__(self):
        """Initialize ConfigFlow."""
        self._fan = Fan(
            "<broadcast>", "1111", "DEFAULT_DEVICEID", "Vento Express", 4000
        )
        # Используем context для хранения, вместо прямого присвоения
        self._reauth_entry_id = None  # Это поле будет установлено через context

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            if user_input[CONF_IP_ADDRESS] == "<broadcast>":
                ip = None
                ips = self._fan.search_devices("0.0.0.0")
                unique_ids = []
                for entry in self._async_current_entries(include_ignore=True):
                    unique_ids.append(entry.unique_id)
                for ip in ips:
                    self._fan.host = ip
                    self._fan.id = user_input[CONF_DEVICE_ID]
                    self._fan.password = user_input[CONF_PASSWORD]
                    self._fan.name = user_input[CONF_NAME]
                    self._fan.port = user_input[CONF_PORT]
                    self._fan.init_device()
                    if self._fan.id not in unique_ids:
                        user_input[CONF_IP_ADDRESS] = ip
                        break
                if user_input[CONF_IP_ADDRESS] == "<broadcast>":
                    raise CannotConnect

            info = await validate_input(self.hass, user_input)
            await self.async_set_unique_id(info["id"])
            self._abort_if_unique_id_configured()
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauthorization (called when integration needs new credentials)."""
        # Сохраняем entry_id в context для использования в следующем шаге
        self.context["reauth_entry_id"] = self.context.get("entry_id")
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        errors = {}
        entry_id = self.context.get("reauth_entry_id")
        if not entry_id:
            entry_id = self.context.get("entry_id")
        
        entry = self.hass.config_entries.async_get_entry(entry_id)
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=user_input,
                    title=info["title"],
                )
                # Перезагружаем интеграцию
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(entry.entry_id)
                )
                return self.async_abort(reason="reauth_successful")
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reauth")
                errors["base"] = "unknown"
        
        current_data = entry.data if entry else {}
        schema = self.add_suggested_values_to_schema(
            STEP_USER_DATA_SCHEMA, current_data
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={"name": entry.title if entry else "device"},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration."""
        errors = {}
        entry_id = self.context.get("entry_id")
        entry = self.hass.config_entries.async_get_entry(entry_id)
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=user_input,
                    title=info["title"],
                )
                # Перезагружаем интеграцию
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(entry.entry_id)
                )
                return self.async_abort(reason="reconfigure_successful")
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during reconfigure")
                errors["base"] = "unknown"
        
        current_data = entry.data if entry else {}
        schema = self.add_suggested_values_to_schema(
            STEP_USER_DATA_SCHEMA, current_data
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
