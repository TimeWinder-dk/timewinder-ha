"""Minimal async client for the TimeWinder Operations Hub API.

Auth model: the Hub issues a 30-day HMAC JWT via an SMS one-time-password flow
(``/api/auth/otp/request`` -> ``/api/auth/otp/verify``). There is no silent refresh,
so when the token expires the integration triggers Home Assistant's reauth flow,
which re-runs the OTP exchange.
"""

from __future__ import annotations

from typing import Any

import aiohttp

_TIMEOUT = aiohttp.ClientTimeout(total=20)


class TimeWinderError(Exception):
    """Base error for the TimeWinder client."""


class TimeWinderAuthError(TimeWinderError):
    """Token missing/expired (HTTP 401) — caller should re-authenticate."""


class TimeWinderForbiddenError(TimeWinderError):
    """Authenticated but not authorised (HTTP 403) — a role problem, not a token problem."""


class TimeWinderApiError(TimeWinderError):
    """Any other API/transport failure."""


class TimeWinderClient:
    """Thin wrapper over the Hub's REST API using HA's shared aiohttp session."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        token: str | None = None,
    ) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        self._token = token

    @property
    def token(self) -> str | None:
        return self._token

    def set_token(self, token: str) -> None:
        self._token = token

    async def request_otp(self, email: str) -> dict[str, Any]:
        """Trigger an SMS one-time code. Returns ``{maskedPhone}``."""
        return await self._request(
            "POST", "/api/auth/otp/request", json={"email": email}, auth=False
        )

    async def verify_otp(self, email: str, code: str) -> dict[str, Any]:
        """Exchange an OTP code for a token. Returns ``{token, expiresIn}``."""
        return await self._request(
            "POST", "/api/auth/otp/verify", json={"email": email, "code": code}, auth=False
        )

    async def get(self, path: str) -> Any:
        """Authenticated GET. Raises TimeWinderAuthError on 401."""
        return await self._request("GET", path, auth=True)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if auth:
            if not self._token:
                raise TimeWinderAuthError("No token configured")
            headers["Authorization"] = f"Bearer {self._token}"

        url = f"{self._base}{path}"
        try:
            async with self._session.request(
                method, url, json=json, headers=headers, timeout=_TIMEOUT
            ) as resp:
                if resp.status == 401:
                    raise TimeWinderAuthError("HTTP 401")
                if resp.status == 403:
                    raise TimeWinderForbiddenError("HTTP 403")
                if resp.status >= 400:
                    body = await resp.text()
                    raise TimeWinderApiError(f"HTTP {resp.status}: {body[:200]}")
                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.text()
        except aiohttp.ClientError as err:
            raise TimeWinderApiError(str(err)) from err
