"""Support for SimpliSafe alarm control panels."""
import logging
import re

from simplipy.entity import EntityTypes
from simplipy.system import SystemStates

from homeassistant.components.alarm_control_panel import (
    FORMAT_NUMBER,
    FORMAT_TEXT,
    AlarmControlPanel,
)
from homeassistant.components.alarm_control_panel.const import (
    SUPPORT_ALARM_ARM_AWAY,
    SUPPORT_ALARM_ARM_HOME,
)
from homeassistant.const import (
    CONF_CODE,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
)
from homeassistant.util.dt import utc_from_timestamp

from . import SimpliSafeEntity
from .const import DATA_CLIENT, DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTR_ALARM_ACTIVE = "alarm_active"
ATTR_ALARM_DURATION = "alarm_duration"
ATTR_ALARM_VOLUME = "alarm_volume"
ATTR_BATTERY_BACKUP_POWER_LEVEL = "battery_backup_power_level"
ATTR_CHIME_VOLUME = "chime_volume"
ATTR_ENTRY_DELAY_AWAY = "entry_delay_away"
ATTR_ENTRY_DELAY_HOME = "entry_delay_home"
ATTR_EXIT_DELAY_AWAY = "exit_delay_away"
ATTR_EXIT_DELAY_HOME = "exit_delay_home"
ATTR_GSM_STRENGTH = "gsm_strength"
ATTR_LAST_EVENT_INFO = "last_event_info"
ATTR_LAST_EVENT_SENSOR_NAME = "last_event_sensor_name"
ATTR_LAST_EVENT_SENSOR_TYPE = "last_event_sensor_type"
ATTR_LAST_EVENT_TIMESTAMP = "last_event_timestamp"
ATTR_LAST_EVENT_TYPE = "last_event_type"
ATTR_LIGHT = "light"
ATTR_RF_JAMMING = "rf_jamming"
ATTR_VOICE_PROMPT_VOLUME = "voice_prompt_volume"
ATTR_WALL_POWER_LEVEL = "wall_power_level"
ATTR_WIFI_STRENGTH = "wifi_strength"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up a SimpliSafe alarm control panel based on existing config."""
    pass


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up a SimpliSafe alarm control panel based on a config entry."""
    simplisafe = hass.data[DOMAIN][DATA_CLIENT][entry.entry_id]
    async_add_entities(
        [
            SimpliSafeAlarm(simplisafe, system, entry.data.get(CONF_CODE))
            for system in simplisafe.systems.values()
        ],
        True,
    )


class SimpliSafeAlarm(SimpliSafeEntity, AlarmControlPanel):
    """Representation of a SimpliSafe alarm."""

    def __init__(self, simplisafe, system, code):
        """Initialize the SimpliSafe alarm."""
        super().__init__(system, "Alarm Control Panel")
        self._changed_by = None
        self._code = code
        self._simplisafe = simplisafe
        self._state = None

        self._attrs.update({ATTR_ALARM_ACTIVE: self._system.alarm_going_off})
        if self._system.version == 3:
            self._attrs.update(
                {
                    ATTR_ALARM_DURATION: self._system.alarm_duration,
                    ATTR_ALARM_VOLUME: self._system.alarm_volume.name,
                    ATTR_BATTERY_BACKUP_POWER_LEVEL: self._system.battery_backup_power_level,
                    ATTR_CHIME_VOLUME: self._system.chime_volume.name,
                    ATTR_ENTRY_DELAY_AWAY: self._system.entry_delay_away,
                    ATTR_ENTRY_DELAY_HOME: self._system.entry_delay_home,
                    ATTR_EXIT_DELAY_AWAY: self._system.exit_delay_away,
                    ATTR_EXIT_DELAY_HOME: self._system.exit_delay_home,
                    ATTR_GSM_STRENGTH: self._system.gsm_strength,
                    ATTR_LIGHT: self._system.light,
                    ATTR_RF_JAMMING: self._system.rf_jamming,
                    ATTR_VOICE_PROMPT_VOLUME: self._system.voice_prompt_volume.name,
                    ATTR_WALL_POWER_LEVEL: self._system.wall_power_level,
                    ATTR_WIFI_STRENGTH: self._system.wifi_strength,
                }
            )

    @property
    def changed_by(self):
        """Return info about who changed the alarm last."""
        return self._changed_by

    @property
    def code_format(self):
        """Return one or more digits/characters."""
        if not self._code:
            return None
        if isinstance(self._code, str) and re.search("^\\d+$", self._code):
            return FORMAT_NUMBER
        return FORMAT_TEXT

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_ALARM_ARM_HOME | SUPPORT_ALARM_ARM_AWAY

    def _validate_code(self, code, state):
        """Validate given code."""
        check = self._code is None or code == self._code
        if not check:
            _LOGGER.warning("Wrong code entered for %s", state)
        return check

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""
        if not self._validate_code(code, "disarming"):
            return

        await self._system.set_off()

    async def async_alarm_arm_home(self, code=None):
        """Send arm home command."""
        if not self._validate_code(code, "arming home"):
            return

        await self._system.set_home()

    async def async_alarm_arm_away(self, code=None):
        """Send arm away command."""
        if not self._validate_code(code, "arming away"):
            return

        await self._system.set_away()

    async def async_update(self):
        """Update alarm status."""
        event_data = self._simplisafe.last_event_data[self._system.system_id]

        if event_data.get("pinName"):
            self._changed_by = event_data["pinName"]

        if self._system.state == SystemStates.error:
            self._online = False
            return

        self._online = True

        if self._system.state == SystemStates.off:
            self._state = STATE_ALARM_DISARMED
        elif self._system.state in (SystemStates.home, SystemStates.home_count):
            self._state = STATE_ALARM_ARMED_HOME
        elif self._system.state in (
            SystemStates.away,
            SystemStates.away_count,
            SystemStates.exit_delay,
        ):
            self._state = STATE_ALARM_ARMED_AWAY
        else:
            self._state = None

        last_event = self._simplisafe.last_event_data[self._system.system_id]
        self._attrs.update(
            {
                ATTR_LAST_EVENT_INFO: last_event["info"],
                ATTR_LAST_EVENT_SENSOR_NAME: last_event["sensorName"],
                ATTR_LAST_EVENT_SENSOR_TYPE: EntityTypes(last_event["sensorType"]).name,
                ATTR_LAST_EVENT_TIMESTAMP: utc_from_timestamp(
                    last_event["eventTimestamp"]
                ),
                ATTR_LAST_EVENT_TYPE: last_event["eventType"],
            }
        )
