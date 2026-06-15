"""Constants for the TimeWinder Operations Hub integration."""

from __future__ import annotations

DOMAIN = "timewinder_ops"

DEFAULT_BASE_URL = "https://drift.timewinder.dk"

CONF_BASE_URL = "base_url"
CONF_EMAIL = "email"
CONF_TOKEN = "token"
CONF_EXPIRY = "expiry"

# The Operations Hub data is minute-fresh; polling every 60s is plenty.
UPDATE_INTERVAL_SECONDS = 60
