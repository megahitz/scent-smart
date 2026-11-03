"""Constants for the Scent Smart (GAS-501F diffuser) integration."""
from __future__ import annotations

DOMAIN = "scent_smart"

MANUFACTURER = "Scent"
MODEL = "GAS-501F"

# BLE
SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Frame framing
FRAME_HEAD = bytes((0x55, 0xAA))
FRAME_TAIL = 0x5A
CMD_ACK_BASE = 0x80

# Commands
CMD_SET_TIME = 0x06
CMD_OPERATION = 0x07
CMD_TIMER = 0x14
CMD_STATE_DUMP = 0x21

# Operation funcs (CMD 0x07, single-byte value)
FUNC_RUNNING_STATUS = 0x12
FUNC_FAN = 0x10
FUNC_CHILD_LOCK = 0x11
FUNC_AMBIENT_LIGHT = 0x15
FUNC_START_DEFAULT_CYCLE = 0x01  # NEVER use as a query: it starts the factory cycle

# Numeric funcs (CMD 0x07, u16 LE)
FUNC_BOTTLE_CAPACITY = 0x31
FUNC_CONSUMPTION = 0x32
FUNC_OIL_AVAILABLE = 0x33

# Timer (CMD 0x14) payload is 16 bytes
TIMER_PAYLOAD_LEN = 16
TIMER_TAIL = 0x00000001  # u32 LE constant tail (validated)

# Mode bitmask meaning "every day"
TIMER_MODE_EVERY_DAY = 0x00FF

# Device limits (validated end-to-end via the official app)
RUN_MIN = 5
RUN_MAX = 200
RUN_STEP = 5
SUSPEND_MIN = 20
SUSPEND_MAX = 300
SUSPEND_STEP = 5

NUM_PROGRAMS = 5

# One-shot spray guard
MIN_SPRAY_GUARD_SECONDS = 3

# Connection behaviour
MAX_WRITE_ATTEMPTS = 3
RECONNECT_MIN_INTERVAL = 5.0

# Default options
DEFAULT_SPRAY_DURATION = 60
DEFAULT_PAUSE_TIME = 200
DEFAULT_WINDOW_START = 480  # 08:00
DEFAULT_WINDOW_STOP = 1320  # 22:00

CONF_BLE_ADDRESS = "ble_address"
CONF_NAME = "friendly_name"

CONF_DEFAULT_SPRAY_DURATION = "default_spray_duration"
CONF_DEFAULT_PAUSE_TIME = "default_pause_time"
CONF_DEFAULT_WINDOW_START = "default_window_start"
CONF_DEFAULT_WINDOW_STOP = "default_window_stop"
CONF_ACTIVE_PROGRAM = "active_program"
CONF_ONESHOT_SPRAY_DURATION = "oneshot_spray_duration"
