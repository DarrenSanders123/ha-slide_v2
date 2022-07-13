"""Config flow for slideV2 integration."""
from __future__ import annotations

import logging
from typing import Any
from attr import has

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from goslideapi.goslideapi import GoSlideCloud, AuthenticationFailed

# from goslideapi import GoSlideCloud, GoSlideLocal

from .const import (
    DOMAIN,
    SLIDES,
    SLIDES_LOCAL,
    DEFAULT_OFFSET,
    DEFAULT_RETRY,
    API_CLOUD,
    API_LOCAL,
)

_LOGGER = logging.getLogger(__name__)


async def authenticate_cloud(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Authenticate with the cloud."""
    try:
        api = GoSlideCloud(
            username=data["username"],
            password=data["password"],
            verify_ssl=data["verify_ssl"],
        )
        await api.login()
        return
    except AuthenticationFailed as err:
        raise AuthenticationFailed from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for slideV2."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_menu(
                step_id="user",
                menu_options={"setup_cloud": "Cloud Api", "setup_local": "Local Api"},
                description_placeholders={
                    "model": "Example model",
                },
            )

    # if user_input["setup_cloud"]:
    async def async_step_setup_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow to setup slideV2 using Cloud Api."""

        errors = {}

        data_schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password"): str,
            }
        )

        if self.show_advanced_options:
            data_schema = data_schema.extend(
                {
                    vol.Required(
                        "host",
                        default="https://api.goslide.com",
                        description="Do not change!",
                    ): str,
                    vol.Optional("verify_ssl", default=True): cv.boolean,
                }
            )

        if user_input is None:
            return self.async_show_form(step_id="setup_cloud", data_schema=data_schema)

        try:
            await authenticate_cloud(self.hass, user_input)
            return self.async_create_entry(
                title="Slide Curtains (Cloud)",
                data={
                    "username": user_input["username"],
                    "password": user_input["password"],
                },
            )
        except AuthenticationFailed as err:
            _LOGGER.error(err)
            errors["base"] = "invalid_auth"
            return self.async_show_form(
                step_id="setup_cloud", data_schema=data_schema, errors=errors
            )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
