"""Sensors for the TimeWinder Operations Hub."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TimeWinderCoordinator


def _dig(data: dict[str, Any], section: str, *keys: str) -> Any:
    """Walk ``data[section][k1][k2]...`` returning None if any hop is missing."""
    cur: Any = data.get(section)
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


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
