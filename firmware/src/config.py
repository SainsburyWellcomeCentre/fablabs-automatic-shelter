"""Arena settings: pins, bus speeds, Harp registers and device identity.

Change values here. The other files read them from this module.
"""

from micropython import const

VM_VOLTAGE = const(12)  # in volts

# ---- Pins (Dynamixel Controller) ---------------------------------------------
PIN_ERROR_LED = const(13)  # active-low: 0 = on
PIN_USER_LED = const(11)
PIN_HARP_LED = const(12)
PIN_STATUS_LED = const(7)  # Harp status LED, driven by microharp
PIN_SYNC_RX = const(1)  # Harp clock sync input
PIN_SERVO_TX = const(8)
PIN_SERVO_RX = const(9)
PIN_SW_CW = const(6)
PIN_SW_CCW = const(4)
PIN_SW_PRESS = const(5)
PIN_SCL = const(23)
PIN_SDA = const(22)
PIN_VM_DET = const(26)
PIN_VM_EN = const(27)

# ---- Speeds ----------------------------------------------------------------
SYNC_BAUD = const(100_000)
SERVO_BAUD = const(1_000_000)
I2C_FREQ = const(400_000)

# ---- Banks ----------------------------------------------------------------
SYNC_BANK = const(0)
SERVO_BANK = const(1)
I2C_BANK = const(1)

# ---- Harp application registers -------------------------------------------
ADDR_POS_HOUSE_1 = const(0x20)
ADDR_POS_HOUSE_2 = const(0x21)
ADDR_POS_HOUSE_3 = const(0x22)
ADDR_POS_DOOR_1 = const(0x23)
ADDR_POS_DOOR_2 = const(0x24)
ADDR_POS_DOOR_3 = const(0x25)
ADDR_POS_BLOCK_1 = const(0x26)
ADDR_POS_BLOCK_2 = const(0x27)
ADDR_POS_ARM = const(0x28)

ADDR_STATUS_HOUSE_1 = const(0x30)
ADDR_STATUS_HOUSE_2 = const(0x31)
ADDR_STATUS_HOUSE_3 = const(0x32)
ADDR_STATUS_DOOR_1 = const(0x33)
ADDR_STATUS_DOOR_2 = const(0x34)
ADDR_STATUS_DOOR_3 = const(0x35)
ADDR_STATUS_BLOCK_1 = const(0x36)
ADDR_STATUS_BLOCK_2 = const(0x37)
ADDR_STATUS_ARM = const(0x38)

ADDR_TRQ_HOUSE_1 = const(0x40)
ADDR_TRQ_HOUSE_2 = const(0x41)
ADDR_TRQ_HOUSE_3 = const(0x42)
ADDR_TRQ_DOOR_1 = const(0x43)
ADDR_TRQ_DOOR_2 = const(0x44)
ADDR_TRQ_DOOR_3 = const(0x45)
ADDR_TRQ_BLOCK_1 = const(0x46)
ADDR_TRQ_BLOCK_2 = const(0x47)
ADDR_TRQ_ARM = const(0x48)

ADDR_SPD_HOUSE_1 = const(0x50)
ADDR_SPD_HOUSE_2 = const(0x51)
ADDR_SPD_HOUSE_3 = const(0x52)
ADDR_SPD_DOOR_1 = const(0x53)
ADDR_SPD_DOOR_2 = const(0x54)
ADDR_SPD_DOOR_3 = const(0x55)
ADDR_SPD_BLOCK_1 = const(0x56)
ADDR_SPD_BLOCK_2 = const(0x57)
ADDR_SPD_ARM = const(0x58)

# ---- Harp device identity -------------------------------------------------
WHO_AM_I = const(3300)
FW_VERSION = (0, 1)
HW_VERSION = (2, 1)
HARP_VERSION = (1, 13)
DEVICE_NAME = b"Automatic Shelter"
