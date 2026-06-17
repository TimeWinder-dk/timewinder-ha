"""Data update coordinator for the TimeWinder Operations Hub."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    TimeWinderApiError,
    TimeWinderAuthError,
    TimeWinderClient,
    TimeWinderForbiddenError,
)
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class TimeWinderCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the Hub once per interval and fans the result out to sensors.

    ``/api/me`` is used as the token probe: it is available to every authenticated
    volunteer, so a 401 there unambiguously means the token is bad/expired and we
    should reauth. The richer endpoints (command-center, analytics) require the
    Drift Coordinator role; a 403 there is a permissions problem, not a token
    problem, so those degrade to ``None`` instead of forcing reauth.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: TimeWinderClient,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            # Token probe — a 401 here means "re-authenticate".
            me = await self.client.get("/api/me")
        except TimeWinderAuthError as err:
            raise ConfigEntryAuthFailed("Token rejected (401)") from err
        except TimeWinderApiError as err:
            raise UpdateFailed(f"/api/me failed: {err}") from err

        return {
            "me": me,
            "command": await self._safe_get("/api/command-center"),
            "incidents": await self._safe_get("/api/incidents?filter=team"),
            "live": await self._safe_get("/api/analytics/live"),
            # Role-gated endpoints — degrade to None (403) instead of failing the update.
            "overview": await self._safe_get("/api/analytics/overview"),
            "delivery": await self._safe_get("/api/delivery-overview"),
            "bar_orders": await self._safe_get("/api/bar-orders"),
        }

    async def _safe_get(self, path: str) -> Any:
        """GET that tolerates role (403) and transient errors, but lets 401 bubble
        up so the parent triggers reauth."""
        try:
            return await self.client.get(path)
        except TimeWinderForbiddenError:
            _LOGGER.debug("%s: 403 (role lacks access) — skipping", path)
            return None
        except TimeWinderApiError as err:
            _LOGGER.debug("%s failed: %s", path, err)
            return None
