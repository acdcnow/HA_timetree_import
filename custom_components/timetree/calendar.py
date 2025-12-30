"""Calendar platform for TimeTree."""
from datetime import datetime, date
import logging

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_CALENDAR_ID, CONF_CALENDAR_NAME
from .coordinator import TimeTreeCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the calendar entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entity = TimeTreeCalendarEntity(
        coordinator, 
        entry.data[CONF_CALENDAR_NAME]
    )
    async_add_entities([entity])


class TimeTreeCalendarEntity(CalendarEntity):
    """Representation of a TimeTree Calendar."""

    def __init__(self, coordinator: TimeTreeCoordinator, name: str):
        """Initialize the entity."""
        self.coordinator = coordinator
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.calendar_id}"
    
    @property
    def event(self):
        """Return the next upcoming event."""
        now = dt_util.now()
        events = self.coordinator.data or []
        
        future_events = []
        for e in events:
            # Handle All-Day Events (Compare Date vs Date)
            if e["all_day"]:
                end_val = e["end"]
                # Safety check: ensure we have a date object
                if isinstance(end_val, datetime):
                    end_val = end_val.date()
                
                if end_val >= now.date():
                    future_events.append(e)
            
            # Handle Regular Events (Compare Datetime vs Datetime)
            else:
                if e["end"] > now:
                    future_events.append(e)
        
        if not future_events:
            return None
            
        # Helper to safely sort mixed date/datetime objects
        def sort_key(x):
            start = x["start"]
            if isinstance(start, datetime):
                return start
            # Convert date to datetime for comparison (assuming start of day local time)
            return dt_util.start_of_local_day(
                datetime.combine(start, datetime.min.time())
            )

        next_event = min(future_events, key=sort_key)
        return self._build_calendar_event(next_event)

    async def async_get_events(self, hass, start_date, end_date):
        """Return calendar events within a range."""
        if self.coordinator.data is None:
            await self.coordinator.async_request_refresh()
            
        events = []
        for event_data in self.coordinator.data or []:
            ev_start = event_data["start"]
            ev_end = event_data["end"]
            
            # Normalize to datetime for comparison if necessary, or rely on duck typing 
            # Note: HA passes start_date/end_date as datetimes.
            
            # For strict correctness with all-day events (dates):
            if event_data["all_day"]:
                # Check if the date range overlaps the datetime range
                # Convert query range to dates
                query_start_date = start_date.date()
                query_end_date = end_date.date()
                
                if ev_start < query_end_date and ev_end > query_start_date:
                    events.append(self._build_calendar_event(event_data))
            else:
                # Standard datetime overlap
                if ev_start < end_date and ev_end > start_date:
                    events.append(self._build_calendar_event(event_data))
                
        return events

    def _build_calendar_event(self, event_data):
        """Convert internal dict to CalendarEvent."""
        return CalendarEvent(
            summary=event_data["summary"],
            start=event_data["start"],
            end=event_data["end"],
            location=event_data["location"],
            description=event_data["description"],
            uid=event_data["uid"],
            rrule=event_data["recurrences"][0] if event_data["recurrences"] else None
        )