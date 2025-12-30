"""DataUpdateCoordinator for TimeTree."""
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, UPDATE_INTERVAL
from .api import TimeTreeApi

_LOGGER = logging.getLogger(__name__)

class TimeTreeCoordinator(DataUpdateCoordinator):
    """Class to manage fetching TimeTree data."""

    def __init__(self, hass, api: TimeTreeApi, calendar_id):
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.api = api
        self.calendar_id = calendar_id

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            raw_events = await self.api.async_get_events(self.calendar_id)
            parsed_events = [self.api.parse_event(e) for e in raw_events]
            return parsed_events
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")