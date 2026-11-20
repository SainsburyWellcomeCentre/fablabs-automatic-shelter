import asyncio

import usb.device
from usb.device.cdc import CDCInterface

from microharp import CdcTransport, HarpDevice

import config as cfg
import shelter
import hardware as hw

# builtin_driver=True keeps the MicroPython REPL on its own USB serial port
# next to the Harp port. mpremote and tracebacks stay available. Set it to
# False for a release build with a single port.
cdc = CDCInterface(baudrate=1_000_000, timeout=0, txbuf=2048, rxbuf=512)
usb.device.get().init(cdc, builtin_driver=True)

device = HarpDevice(
    transport=CdcTransport(cdc),
    sync_uart=hw.sync_uart,
    led_pin=hw.status_led,
    who_am_i=cfg.WHO_AM_I,
    fw_version=cfg.FW_VERSION,
    hw_version=cfg.HW_VERSION,
    harp_version=cfg.HARP_VERSION,
    device_name=cfg.DEVICE_NAME,
)

shelter.attach(device)

asyncio.run(device.run())



