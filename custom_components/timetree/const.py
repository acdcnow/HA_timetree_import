"""Constants for the TimeTree integration."""
from datetime import timedelta

DOMAIN = "timetree"
CONF_CALENDAR_ID = "calendar_id"
CONF_CALENDAR_NAME = "calendar_name"

# Update frequency as requested
UPDATE_INTERVAL = timedelta(minutes=60)

LOGGER_NAME = "custom_components.timetree"