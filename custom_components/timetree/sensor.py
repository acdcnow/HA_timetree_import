"""Sensor platform for TimeTree."""
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from .const import DOMAIN, CONF_CALENDAR_NAME
from .coordinator import TimeTreeCoordinator

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data[CONF_CALENDAR_NAME]
    
    async_add_entities([TimeTreeLastUpdatedSensor(coordinator, name)])

class TimeTreeLastUpdatedSensor(SensorEntity):
    """Sensor showing the last time data was successfully fetched."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator: TimeTreeCoordinator, calendar_name: str):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Last Updated"
        self._attr_unique_id = f"{coordinator.calendar_id}_last_updated"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.last_update_success_time

    @property
    def available(self):
        """Return if entity is available."""
        # Fix: Use standard coordinator property for availability
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()