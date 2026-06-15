"""Constants for the TimeWinder Operations Hub integration."""

from __future__ import annotations

DOMAIN = "timewinder_ops"

# The API lives on the Azure Functions host, NOT the SPA frontend (drift.timewinder.dk
# is static-only — POSTing there returns 405). See frontend/.env.production.
DEFAULT_BASE_URL = "https://tw-opshub-func.azurewebsites.net"

CONF_BASE_URL = "base_url"
CONF_EMAIL = "email"
CONF_TOKEN = "token"
CONF_EXPIRY = "expiry"

# The Operations Hub data is minute-fresh; polling every 60s is plenty.
UPDATE_INTERVAL_SECONDS = 60
