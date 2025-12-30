"""Config flow for TimeTree integration."""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback

from .const import DOMAIN, CONF_CALENDAR_ID, CONF_CALENDAR_NAME
from .api import TimeTreeApi, TimeTreeAuthError

_LOGGER = logging.getLogger(__name__)

class TimeTreeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TimeTree."""

    VERSION = 1

    def __init__(self):
        """Initialize."""
        self._api = None
        self._calendars = None
        self._auth_data = {}

    async def async_step_user(self, user_input=None):
        """Step 1: Get Email and Password."""
        errors = {}

        if user_input is not None:
            self._auth_data = user_input
            self._api = TimeTreeApi(self.hass, user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            
            try:
                # Validate and fetch calendars immediately to prepare for next step
                self._calendars = await self._api.async_validate_and_get_calendars()
                return await self.async_step_calendar()
            except TimeTreeAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )

    async def async_step_calendar(self, user_input=None):
        """Step 2: Select a Calendar."""
        errors = {}
        
        if user_input is not None:
            # Find the name of the selected calendar
            selected_cal_id = user_input[CONF_CALENDAR_ID]
            selected_cal_name = next(
                (c["name"] for c in self._calendars if str(c["id"]) == selected_cal_id), 
                "TimeTree Calendar"
            )

            # Create the config entry
            return self.async_create_entry(
                title=selected_cal_name,
                data={
                    **self._auth_data,
                    CONF_CALENDAR_ID: selected_cal_id,
                    CONF_CALENDAR_NAME: selected_cal_name
                },
            )

        # Prepare options for the dropdown
        calendar_options = {str(c["id"]): c["name"] for c in self._calendars}

        return self.async_show_form(
            step_id="calendar",
            data_schema=vol.Schema({
                vol.Required(CONF_CALENDAR_ID): vol.In(calendar_options),
            }),
            errors=errors,
        )