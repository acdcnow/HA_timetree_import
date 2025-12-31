"""API Client for TimeTree."""
import logging
import uuid
import requests
import json
from datetime import datetime, timedelta
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

        _LOGGER.debug("Attempting Login for user: %s", self._email)

        try:
            response = self._session.put(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code != 200:
                _LOGGER.error("Login failed. Status: %s, Response: %s", response.status_code, response.text)
                raise TimeTreeAuthError("Invalid credentials")
            
            self._session_id = response.cookies.get("_session_id")
            self._session.cookies.set("_session_id", self._session_id)
            _LOGGER.debug("Login successful. Session ID acquired.")
            return True
        except requests.RequestException as e:
            _LOGGER.error("Login connection error: %s", e)
            raise TimeTreeAuthError(f"Connection error: {e}")

    def _get_calendars(self):
        """Get list of calendars."""
        if not self._session_id:
            self._login()

        url = f"{API_BASEURI}/calendars?since=0"
        headers = {"X-Timetreea": API_USER_AGENT}
        
        _LOGGER.debug("Fetching Calendars...")
        response = self._session.get(url, headers=headers)
        
        if response.status_code == 401:
            _LOGGER.debug("Token expired during calendar fetch. Re-logging in.")
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
        """Recursive fetch for events if chunked."""
        url = f"{API_BASEURI}/calendar/{calendar_id}/events/sync?since={since}"
        headers = {"X-Timetreea": API_USER_AGENT}
        
        _LOGGER.debug("Fetching chunked events since: %s", since)
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

        _LOGGER.debug("Fetching events for calendar: %s", calendar_id)
        response = self._session.get(url, headers=headers)
        
        if response.status_code == 401:
            _LOGGER.debug("Token expired during event fetch. Re-logging in.")
            self._login()
            response = self._session.get(url, headers=headers)
            
        response.raise_for_status()
        r_json = response.json()
        
        events = r_json.get("events", [])
        if r_json.get("chunk") is True:
            events.extend(self._get_events_recur(calendar_id, r_json["since"]))
            
        _LOGGER.debug("Fetched %s events.", len(events))
        return events

    def _create_event(self, calendar_id, event_data):
        """Create a new event in TimeTree."""
        if not self._session_id:
            self._login()

        url = f"{API_BASEURI}/calendar/{calendar_id}/events"
        headers = {
            "Content-Type": "application/json",
            "X-Timetreea": API_USER_AGENT
        }
        
        payload = {
            "type": 0,
            "category": 1,
            "title": event_data.get("summary", "New Event"),
            "note": event_data.get("description", ""),
            "location": event_data.get("location", ""),
            "all_day": event_data.get("all_day", False),
            "start_at": event_data.get("start_at"),
            "start_timezone": event_data.get("timezone", "UTC"),
            "end_at": event_data.get("end_at"),
            "end_timezone": event_data.get("timezone", "UTC"),
            "uuid": str(uuid.uuid4())
        }

        # DEBUG LOGGING FOR PAYLOAD
        _LOGGER.debug("Sending Create Event Payload: %s", json.dumps(payload, default=str))

        response = self._session.post(url, json=payload, headers=headers)
        
        if response.status_code == 401:
            _LOGGER.debug("Token expired during create event. Re-logging in.")
            self._login()
            response = self._session.post(url, json=payload, headers=headers)

        # DEBUG LOGGING FOR RESPONSE
        _LOGGER.debug("TimeTree Create Response [%s]: %s", response.status_code, response.text)

        if response.status_code not in (200, 201):
            _LOGGER.error("Failed to create event. Status: %s, Body: %s", response.status_code, response.text)
            raise Exception(f"API Error {response.status_code}: {response.text}")
            
        return response.json()

    async def async_validate_and_get_calendars(self):
        return await self._hass.async_add_executor_job(self._do_validate)

    def _do_validate(self):
        self._login()
        return self._get_calendars()

    async def async_get_events(self, calendar_id):
        return await self._hass.async_add_executor_job(self._get_events, calendar_id)

    async def async_create_event(self, calendar_id, event_payload):
        return await self._hass.async_add_executor_job(self._create_event, calendar_id, event_payload)

    @staticmethod
    def parse_event(event_data):
        start_ts = event_data.get("start_at", 0)
        end_ts = event_data.get("end_at", 0)
        start_tz = event_data.get("start_timezone", "UTC")
        end_tz = event_data.get("end_timezone", "UTC")
        all_day = event_data.get("all_day", False)

        def convert_ts(ts, tz_name):
            try:
                if ts >= 0:
                    dt = datetime.fromtimestamp(ts / 1000, ZoneInfo(tz_name))
                else:
                    dt = datetime.fromtimestamp(0, ZoneInfo(tz_name)) + timedelta(seconds=int(ts/1000))
                return dt
            except Exception:
                return datetime.now(ZoneInfo(tz_name))

        start_dt = convert_ts(start_ts, start_tz)
        end_dt = convert_ts(end_ts, end_tz)

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