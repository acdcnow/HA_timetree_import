"""API Client for TimeTree, adapted from eoleedi/timetree-exporter."""
import logging
import uuid
import requests
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

API_BASEURI = "https://timetreeapp.com/api/v1"
API_USER_AGENT = "web/2.1.0/en"

class TimeTreeAuthError(Exception):
    """Raised when login fails."""

class TimeTreeApi:
    """TimeTree API Client."""

    def __init__(self, hass: HomeAssistant, email: str, password: str):
        self._hass = hass
        self._email = email
        self._password = password
        self._session_id = None
        self._session = requests.Session()

    def _login(self):
        """Log in to TimeTree and get session ID."""
        url = f"{API_BASEURI}/auth/email/signin"
        payload = {
            "uid": self._email,
            "password": self._password,
            "uuid": str(uuid.uuid4()).replace("-", ""),
        }
        headers = {
            "Content-Type": "application/json",
            "X-Timetreea": API_USER_AGENT,
        }

        try:
            response = self._session.put(url, json=payload, headers=headers, timeout=10)
            if response.status_code != 200:
                _LOGGER.error("Login failed: %s", response.text)
                raise TimeTreeAuthError("Invalid credentials")
            
            self._session_id = response.cookies.get("_session_id")
            self._session.cookies.set("_session_id", self._session_id)
            return True
        except requests.RequestException as e:
            raise TimeTreeAuthError(f"Connection error: {e}")

    def _get_calendars(self):
        """Get list of calendars."""
        if not self._session_id:
            self._login()

        url = f"{API_BASEURI}/calendars?since=0"
        headers = {"X-Timetreea": API_USER_AGENT}
        
        response = self._session.get(url, headers=headers)
        if response.status_code == 401:
            self._login()
            response = self._session.get(url, headers=headers)

        response.raise_for_status()
        data = response.json()
        return [
            {"id": c["id"], "name": c["name"], "code": c.get("alias_code")}
            for c in data.get("calendars", [])
            if c.get("deactivated_at") is None
        ]

    def _get_events_recur(self, calendar_id, since):
        """Recursive fetch for events."""
        url = f"{API_BASEURI}/calendar/{calendar_id}/events/sync?since={since}"
        headers = {"X-Timetreea": API_USER_AGENT}
        
        response = self._session.get(url, headers=headers)
        response.raise_for_status()
        r_json = response.json()
        
        events = r_json.get("events", [])
        if r_json.get("chunk") is True:
            events.extend(self._get_events_recur(calendar_id, r_json["since"]))
        
        return events

    def _get_events(self, calendar_id):
        """Fetch all events for a specific calendar."""
        if not self._session_id:
            self._login()
            
        url = f"{API_BASEURI}/calendar/{calendar_id}/events/sync"
        headers = {"X-Timetreea": API_USER_AGENT}

        response = self._session.get(url, headers=headers)
        if response.status_code == 401:
            self._login()
            response = self._session.get(url, headers=headers)
            
        response.raise_for_status()
        r_json = response.json()
        
        events = r_json.get("events", [])
        if r_json.get("chunk") is True:
            events.extend(self._get_events_recur(calendar_id, r_json["since"]))
            
        return events

    async def async_validate_and_get_calendars(self):
        """Validate credentials and return available calendars."""
        return await self._hass.async_add_executor_job(self._do_validate)

    def _do_validate(self):
        self._login()
        return self._get_calendars()

    async def async_get_events(self, calendar_id):
        """Fetch events async."""
        return await self._hass.async_add_executor_job(self._get_events, calendar_id)

    @staticmethod
    def parse_event(event_data):
        """Parse raw JSON event into a usable dict."""
        start_ts = event_data.get("start_at", 0)
        end_ts = event_data.get("end_at", 0)
        start_tz = event_data.get("start_timezone", "UTC")
        end_tz = event_data.get("end_timezone", "UTC")
        all_day = event_data.get("all_day", False)

        def convert_ts(ts, tz_name):
            if ts >= 0:
                dt = datetime.fromtimestamp(ts / 1000, ZoneInfo(tz_name))
            else:
                dt = datetime.fromtimestamp(0, ZoneInfo(tz_name)) + timedelta(seconds=int(ts/1000))
            return dt

        start_dt = convert_ts(start_ts, start_tz)
        end_dt = convert_ts(end_ts, end_tz)

        # Fix: Convert to date object if all_day is True
        if all_day:
            start_val = start_dt.date()
            end_val = end_dt.date()
        else:
            start_val = start_dt
            end_val = end_dt

        return {
            "uid": event_data.get("uuid"),
            "summary": event_data.get("title", "No Title"),
            "start": start_val,
            "end": end_val,
            "all_day": all_day,
            "location": event_data.get("location"),
            "description": event_data.get("note"),
            "recurrences": event_data.get("recurrences"),
            "updated_at": event_data.get("updated_at")
        }