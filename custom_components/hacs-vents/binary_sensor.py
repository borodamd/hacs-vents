"""Vento fan binary sensors."""

from __future__ import annotations

from vents_breezy import Fan

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VentoFanDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the entities."""
    coordinator: VentoFanDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
    
    entities = [
        VentoBinarySensor(
            coordinator,
            config,
            "_timer_mode",
            "timer_mode",
            "Timer Mode",
            True,
            "mdi:timer",
        ),
        VentoBinarySensor(
            coordinator,
            config,
            "_filter_replacement_status",
            "filter_replacement_status",
            "Filter Replacement Required",
            True,
            "mdi:air-filter",
            BinarySensorDeviceClass.PROBLEM,
        ),
        VentoBinarySensor(
            coordinator,
            config,
            "_alarm_status",
            "alarm_status",
            "Alarm Status",
            True,
            "mdi:alarm",
            BinarySensorDeviceClass.PROBLEM,
        ),
        VentoBinarySensor(
            coordinator,
            config,
            "_heater_status",
            "heater_status",
            "Heater Status",
            True,
            "mdi:radiator",
            BinarySensorDeviceClass.HEAT,
        ),
        VentoBinarySensor(
            coordinator,
            config,
            "_cloud_server_state",
            "cloud_server_state",
            "Cloud Server State",
            True,
            "mdi:cloud",
            BinarySensorDeviceClass.CONNECTIVITY,
        ),
    ]
    
    async_add_entities(entities)


class VentoBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Vento Binary Sensor class."""

    def __init__(
        self,
        coordinator: VentoFanDataUpdateCoordinator,
        config: ConfigEntry,
        name_suffix: str,
        method_name: str,
        friendly_name: str,
        enable_by_default: bool = True,
        icon: str | None = None,
        device_class: str | None = None,
    ) -> None:
        """Initialize fan binary sensors."""
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_unique_id = f"{self._fan.id}{name_suffix}"
        self._attr_name = f"{self._fan.name} {friendly_name}"
        self._attr_entity_registry_enabled_default = enable_by_default
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._method_name = method_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        method = getattr(self._fan, self._method_name, None)
        if method is None:
            return None
        
        # Методы возвращают boolean
        result = method
        # Для alarm_status и filter_replacement_status обычно True = проблема
        if self._attr_device_class == BinarySensorDeviceClass.PROBLEM:
            return bool(result)
        return bool(result)
