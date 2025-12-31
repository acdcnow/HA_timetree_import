"""DataUpdateCoordinator for TimeTree."""
import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .const import DOMAIN, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .api import TimeTreeApi

_LOGGER = logging.getLogger(__name__)

class TimeTreeCoordinator(DataUpdateCoordinator):
    """Class to manage fetching TimeTree data."""

    def __init__(self, hass, api: TimeTreeApi, calendar_id, entry):
        """Initialize."""
        
        # Determine scan interval
        interval_minutes = entry.options.get(
            CONF_SCAN_INTERVAL, 
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        
        _LOGGER.debug("Initializing coordinator with update interval: %s minutes", interval_minutes)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval_minutes),
        )
        self.api = api
        self.calendar_id = calendar_id
        
        # FIX: Explicitly initialize the attribute needed by the sensor
        self.last_update_success_time = None

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            raw_events = await self.api.async_get_events(self.calendar_id)
            parsed_events = [self.api.parse_event(e) for e in raw_events]
            
            # FIX: Update the timestamp on success
            self.last_update_success_time = dt_util.now()
            
            return parsed_events
        except Exception as err:
            _LOGGER.error("Error updating TimeTree data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}")