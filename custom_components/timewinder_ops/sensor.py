"""Sensors for the TimeWinder Operations Hub."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_ID_PREFIX
from .coordinator import TimeWinderCoordinator


def _dig(data: dict[str, Any], section: str, *keys: str) -> Any:
    """Walk ``data[section][k1][k2]...`` returning None if any hop is missing."""
    cur: Any = data.get(section)
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _cmd(data: dict[str, Any]) -> dict[str, Any] | None:
    """The command-center payload, or None when the account can't see it (403)."""
    cmd = data.get("command")
    return cmd if isinstance(cmd, dict) else None


def _team_count(data: dict[str, Any]) -> int | None:
    cmd = _cmd(data)
    return None if cmd is None else len(cmd.get("teamLoad") or [])


def _need_help(data: dict[str, Any]) -> int | None:
    cmd = _cmd(data)
    if cmd is None:
        return None
    return sum(
        int((t.get("counts") or {}).get("NeedHelp", 0) or 0)
        for t in (cmd.get("availabilityByTeam") or [])
    )


def _top_points_count(data: dict[str, Any]) -> int | None:
    cmd = _cmd(data)
    return None if cmd is None else len(cmd.get("topPoints") or [])


def _delivery_count(data: dict[str, Any]) -> int | None:
    dv = data.get("delivery")
    if not isinstance(dv, dict):
        return None
    rows = dv.get("rows")
    return len(rows) if isinstance(rows, list) else 0


def _bar_orders_count(data: dict[str, Any]) -> int | None:
    bo = data.get("bar_orders")
    return len(bo) if isinstance(bo, list) else None


@dataclass(frozen=True, kw_only=True)
class TWSensorDescription(SensorEntityDescription):
    """Sensor description with value + optional attribute extractors."""

    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None


SENSORS: tuple[TWSensorDescription, ...] = (
    TWSensorDescription(
        key="open_total",
        name="Åbne sager",
        icon="mdi:alert-circle",
        value_fn=lambda d: _dig(d, "command", "open", "total"),
        attr_fn=lambda d: _dig(d, "command", "open") or None,
    ),
    TWSensorDescription(
        key="new_in_window",
        name="Nye sager",
        icon="mdi:alert-plus",
        value_fn=lambda d: _dig(d, "command", "newInWindow"),
    ),
    TWSensorDescription(
        key="open_followups",
        name="Åbne eskaleringer",
        icon="mdi:bell-alert",
        value_fn=lambda d: _dig(d, "command", "escalations", "openFollowUps"),
        attr_fn=lambda d: {"items": _dig(d, "command", "escalations", "items") or []},
    ),
    TWSensorDescription(
        key="sms_failed",
        name="SMS fejlet",
        icon="mdi:message-alert",
        value_fn=lambda d: _dig(d, "command", "sms", "failed"),
    ),
    TWSensorDescription(
        key="users_online",
        name="Brugere online",
        icon="mdi:account-multiple",
        value_fn=lambda d: (d.get("live") or {}).get("users"),
    ),
    TWSensorDescription(
        key="incidents",
        name="Sagsliste",
        icon="mdi:format-list-bulleted",
        value_fn=lambda d: len(d.get("incidents") or []),
        attr_fn=lambda d: {"items": (d.get("incidents") or [])[:25]},
    ),
    # ── From the command-center payload we already fetch (no extra API call) ──
    TWSensorDescription(
        key="need_help",
        name="Brug for hjælp",
        icon="mdi:hand-heart",
        value_fn=_need_help,
        attr_fn=lambda d: {"teams": (_cmd(d) or {}).get("availabilityByTeam") or []}
        if _cmd(d) is not None
        else None,
    ),
    TWSensorDescription(
        key="team_load",
        name="Team-load",
        icon="mdi:account-group",
        value_fn=_team_count,
        attr_fn=lambda d: {"teams": (_cmd(d) or {}).get("teamLoad") or []}
        if _cmd(d) is not None
        else None,
    ),
    TWSensorDescription(
        key="top_points",
        name="Top-punkter",
        icon="mdi:map-marker-alert",
        value_fn=_top_points_count,
        attr_fn=lambda d: {"points": (_cmd(d) or {}).get("topPoints") or []}
        if _cmd(d) is not None
        else None,
    ),
    TWSensorDescription(
        key="response_ack",
        name="Svartid (ack)",
        icon="mdi:timer-outline",
        native_unit_of_measurement="min",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _dig(d, "command", "responseTimes", "toAckMinutes"),
        attr_fn=lambda d: _dig(d, "command", "responseTimes") or None,
    ),
    # ── analytics/overview (one extra call; Coordinator role) ──
    TWSensorDescription(
        key="sessions",
        name="Sessioner",
        icon="mdi:chart-line",
        value_fn=lambda d: _dig(d, "overview", "totals", "sessions"),
        attr_fn=lambda d: {
            "users": _dig(d, "overview", "totals", "users"),
            "pageViews": _dig(d, "overview", "totals", "pageViews"),
            "events": _dig(d, "overview", "totals", "events"),
            "days": _dig(d, "overview", "days"),
            "series": _dig(d, "overview", "series") or [],
        }
        if isinstance(d.get("overview"), dict)
        else None,
    ),
    # ── delivery-overview (Varegaard/Sekretariat role) ──
    TWSensorDescription(
        key="delivery",
        name="Levering",
        icon="mdi:truck-delivery",
        value_fn=_delivery_count,
        attr_fn=lambda d: {
            "from": (d.get("delivery") or {}).get("from"),
            "to": (d.get("delivery") or {}).get("to"),
            "salesAvailable": (d.get("delivery") or {}).get("salesAvailable"),
            "warnings": (d.get("delivery") or {}).get("warnings") or [],
            "rows": ((d.get("delivery") or {}).get("rows") or [])[:50],
        }
        if isinstance(d.get("delivery"), dict)
        else None,
    ),
    # ── bar-orders (fulfiller role) ──
    TWSensorDescription(
        key="bar_orders",
        name="Bar-ordrer",
        icon="mdi:glass-mug-variant",
        value_fn=_bar_orders_count,
        attr_fn=lambda d: {"items": (d.get("bar_orders") or [])[:25]}
        if isinstance(d.get("bar_orders"), list)
        else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TimeWinder sensors from a config entry."""
    coordinator: TimeWinderCoordinator = entry.runtime_data
    async_add_entities(
        TimeWinderSensor(coordinator, entry, description) for description in SENSORS
    )


class TimeWinderSensor(CoordinatorEntity[TimeWinderCoordinator], SensorEntity):
    """A single value derived from the coordinator's combined snapshot."""

    entity_description: TWSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TimeWinderCoordinator,
        entry: ConfigEntry,
        description: TWSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        # Deterministic id (e.g. sensor.timewinder_operations_hub_open_total) — used as the
        # suggested object_id on first registration, regardless of device-name slugging.
        self.entity_id = f"sensor.{ENTITY_ID_PREFIX}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="TimeWinder Operations Hub",
            manufacturer="TimeWinder",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)
