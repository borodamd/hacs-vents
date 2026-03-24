"""EcoVentV2 platform sensors."""
from __future__ import annotations

from vents_breezy import Fan

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, REVOLUTIONS_PER_MINUTE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VentoFanDataUpdateCoordinator

import re


def format_duration_hours(total_hours: float) -> str:
    """Format total hours into years, months, days, hours, minutes."""
    if total_hours is None or total_hours == 0:
        return "0 minutes"
    
    total_minutes = int(total_hours * 60)
    
    # Разбиваем на компоненты
    years = total_minutes // (365 * 24 * 60)
    total_minutes %= (365 * 24 * 60)
    
    months = total_minutes // (30 * 24 * 60)  # Приблизительно
    total_minutes %= (30 * 24 * 60)
    
    days = total_minutes // (24 * 60)
    total_minutes %= (24 * 60)
    
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years > 1 else ''}")
    if months > 0:
        parts.append(f"{months} month{'s' if months > 1 else ''}")
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    
    return ", ".join(parts) if parts else "0 minutes"


async def async_setup_entry(
    hass: HomeAssistant,
    config: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vento Sensors."""
    async_add_entities(
        [
            VentoSensor(
                hass,
                config,
                "_speed1",
                "fan1_speed",
                REVOLUTIONS_PER_MINUTE,
                None,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:fan-speed-1",
            ),
            VentoSensor(
                hass,
                config,
                "_speed2",
                "fan2_speed",
                REVOLUTIONS_PER_MINUTE,
                None,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:fan-speed-2",
            ),
            VentoSensor(
                hass,
                config,
                "_airflow",
                "airflow",
                None,
                None,
                None,
                None,
                True,
                "mdi:air-filter",
            ),
            VentoSensor(
                hass,
                config,
                "_timer_counter",
                "timer_counter",
                "h",
                SensorDeviceClass.DURATION,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:timer-outline",
            ),
            VentoSensor(
                hass,
                config,
                "_battery",
                "battery_voltage",
                PERCENTAGE,
                SensorDeviceClass.BATTERY,
                SensorStateClass.MEASUREMENT,
                EntityCategory.DIAGNOSTIC,
                False,
                "mdi:battery",
            ),
            VentoDurationSensor(
                hass,
                config,
                "_filter_change_in",
                "filter_timer_countdown",
                SensorDeviceClass.DURATION,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:timer-sand",
            ),
            VentoDurationSensor(
                hass,
                config,
                "_machine_hours",
                "machine_hours",
                SensorDeviceClass.DURATION,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:timer-outline",
            ),
            VentoSensor(
                hass,
                config,
                "_ip",
                "current_wifi_ip",
                None,
                None,
                None,
                EntityCategory.DIAGNOSTIC,
                True,
                "mdi:ip-network",
            ),
        ]
    )


# VentoSensor class for numeric/string sensors
class VentoSensor(CoordinatorEntity, SensorEntity):
    """Class for Vento Fan Sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        name_suffix: str,
        method_name: str,
        native_unit_of_measurement=None,
        device_class=None,
        state_class=None,
        entity_category=None,
        enable_by_default=True,
        icon=None,
    ) -> None:
        """Initialize fan sensors."""
        coordinator: VentoFanDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_native_unit_of_measurement = native_unit_of_measurement
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        self._attr_name = self._fan.name + name_suffix
        self._attr_unique_id = self._fan.id + name_suffix
        self._attr_entity_registry_enabled_default = enable_by_default
        self._method_name = method_name
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    @property
    def native_value(self):
        """Get native value property from method."""
        method = getattr(self, self._method_name, None)
        if method:
            return method()
        return None

    def fan1_speed(self):
        """Get fan1 speed value."""
        return self._fan.fan1_speed

    def fan2_speed(self):
        """Get fan2 speed value."""
        return self._fan.fan2_speed

    def airflow(self):
        """Get airflow value."""
        return self._fan.airflow

    def battery_voltage(self):
        """Get battery used percentage."""
        high = 3300
        low = 2500
        if self._fan.battery_voltage is None:
            voltage = 0
        else:
            voltage = int(self._fan.battery_voltage.split()[0])
            voltage = round(((voltage - low) / (high - low)) * 100)
        return voltage

    def timer_counter(self):
        """Get timer counter value as total hours."""
        timer_counter_str = self._fan.timer_counter

        match = re.match(r"(\d+)h (\d+)m (\d+)s", timer_counter_str)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))

            total_hours = hours + minutes / 60 + seconds / 3600
            return round(total_hours, 1)
        return None

    def current_wifi_ip(self):
        """Get current wifi IP value."""
        return self._fan.curent_wifi_ip


# VentoDurationSensor class for duration sensors with numeric value + formatted attribute
class VentoDurationSensor(CoordinatorEntity, SensorEntity):
    """Class for Vento Fan Duration Sensors (filter change, machine hours)."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        name_suffix: str,
        method_name: str,
        device_class=None,
        entity_category=None,
        enable_by_default=True,
        icon=None,
    ) -> None:
        """Initialize duration sensors."""
        coordinator: VentoFanDataUpdateCoordinator = hass.data[DOMAIN][config.entry_id]
        super().__init__(coordinator)
        self._fan: Fan = coordinator._fan
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_name = self._fan.name + name_suffix
        self._attr_unique_id = self._fan.id + name_suffix
        self._attr_entity_registry_enabled_default = enable_by_default
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = "h"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._method_name = method_name
        self._attr_extra_state_attributes = {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=self._fan.name,
        )

    @property
    def native_value(self) -> float | None:
        """Get numeric duration in hours."""
        method = getattr(self, self._method_name, None)
        if method:
            return method()
        return None

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        method = getattr(self, self._method_name, None)
        if method:
            total_hours = method()
            if total_hours is not None:
                formatted = format_duration_hours(total_hours)
                return {"formatted": formatted}
        return {}

    def filter_timer_countdown(self):
        """Get filter time countdown as total hours."""
        remaining_time_str = self._fan.filter_timer_countdown

        match = re.match(r"(\d+)d (\d+)h (\d+)m", remaining_time_str)
        if match:
            days = int(match.group(1))
            hours = int(match.group(2))
            minutes = int(match.group(3))

            total_hours = days * 24 + hours + minutes / 60
            return round(total_hours, 1)
        return None

    def machine_hours(self):
        """Get machine hours value as total hours."""
        machine_hours_str = self._fan.machine_hours

        match = re.match(r"(\d+)d (\d+)h (\d+)m", machine_hours_str)
        if match:
            days = int(match.group(1))
            hours = int(match.group(2))
            minutes = int(match.group(3))

            total_hours = days * 24 + hours + minutes / 60
            return round(total_hours, 1)
        return None
