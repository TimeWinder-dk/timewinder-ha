"""Config + reauth flow (SMS OTP) for the TimeWinder Operations Hub."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    TimeWinderApiError,
    TimeWinderAuthError,
    TimeWinderClient,
    TimeWinderForbiddenError,
)
from .const import (
    CONF_BASE_URL,
    CONF_EMAIL,
    CONF_EXPIRY,
    CONF_TOKEN,
    DEFAULT_BASE_URL,
    DOMAIN,
)


class TimeWinderConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step OTP flow: send code, then verify. Same steps power reauth."""

    VERSION = 1

    def __init__(self) -> None:
        self._base_url: str = DEFAULT_BASE_URL
        self._email: str = ""

    # ── Initial setup ─────────────────────────────────────────────────────────
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._base_url = user_input[CONF_BASE_URL].rstrip("/")
            self._email = user_input[CONF_EMAIL].strip().lower()
            client = TimeWinderClient(async_get_clientsession(self.hass), self._base_url)
            try:
                await client.request_otp(self._email)
            except TimeWinderApiError:
                errors["base"] = "request_failed"
            else:
                return await self.async_step_otp()

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=self._base_url): str,
                vol.Required(CONF_EMAIL, default=self._email): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = TimeWinderClient(async_get_clientsession(self.hass), self._base_url)
            try:
                result = await client.verify_otp(self._email, user_input["code"].strip())
            except (TimeWinderAuthError, TimeWinderApiError):
                errors["base"] = "invalid_code"
            else:
                await self.async_set_unique_id(self._email)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"TimeWinder ({self._email})",
                    data={
                        CONF_BASE_URL: self._base_url,
                        CONF_EMAIL: self._email,
                        CONF_TOKEN: result["token"],
                        CONF_EXPIRY: result.get("expiresIn"),
                    },
                )

        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required("code"): str}),
            errors=errors,
            description_placeholders={"email": self._email},
        )

    # ── Reauth (token expired) ─────────────────────────────────────────────────
    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        self._base_url = entry_data[CONF_BASE_URL]
        self._email = entry_data[CONF_EMAIL]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        client = TimeWinderClient(async_get_clientsession(self.hass), self._base_url)

        if user_input is None:
            # Showing the form: push a fresh code so the user has one to type.
            try:
                await client.request_otp(self._email)
            except TimeWinderApiError:
                errors["base"] = "request_failed"
        else:
            try:
                result = await client.verify_otp(self._email, user_input["code"].strip())
            except (TimeWinderAuthError, TimeWinderForbiddenError, TimeWinderApiError):
                errors["base"] = "invalid_code"
            else:
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                assert entry is not None
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_TOKEN: result["token"],
                        CONF_EXPIRY: result.get("expiresIn"),
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required("code"): str}),
            errors=errors,
            description_placeholders={"email": self._email},
        )
