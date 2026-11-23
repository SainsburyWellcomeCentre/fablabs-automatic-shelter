"""Creates every hardware object once, at import.

main.py and test.py both import from here, so the pin setup lives in one
place. Pin numbers and bus speeds come from config.py.
"""

from dac5571 import VMControl
from machine import Pin, UART, I2C

import config as cfg
from motor import House, Door, Block, Arm

user_led = Pin(cfg.PIN_USER_LED, Pin.OUT, value=1)  # starts off
error_led = Pin(cfg.PIN_ERROR_LED, Pin.OUT, value=1)  # starts off
harp_led = Pin(cfg.PIN_HARP_LED, Pin.OUT, value=0)
status_led = Pin(cfg.PIN_STATUS_LED, Pin.OUT, value=1)

sync_uart = UART(cfg.SYNC_BANK, baudrate=cfg.SYNC_BAUD, rx=Pin(cfg.PIN_SYNC_RX))
servo_uart = UART(cfg.SERVO_BANK, baudrate=cfg.SERVO_BAUD, tx=Pin(cfg.PIN_SERVO_TX), rx=Pin(cfg.PIN_SERVO_RX))

i2c = I2C(cfg.I2C_BANK, scl=Pin(cfg.PIN_SCL), sda=Pin(cfg.PIN_SDA), freq=cfg.I2C_FREQ)
vm = VMControl(i2c, enable_pin=cfg.PIN_VM_EN)
vm.set_voltage(cfg.VM_VOLTAGE)
vm.enabled = True

import time
time.sleep(1)  # give the VM some time to stabilize

house_1 = House(uart=servo_uart, motor_id=3, pos_offset=0)
house_2 = House(uart=servo_uart, motor_id=5, pos_offset=0)
house_3 = House(uart=servo_uart, motor_id=7, pos_offset=0)
door_1 = Door(uart=servo_uart, motor_id=2, pos_offset=0)
door_2 = Door(uart=servo_uart, motor_id=4, pos_offset=0)
door_3 = Door(uart=servo_uart, motor_id=6, pos_offset=0)
block_1 = Block(uart=servo_uart, motor_id=8, pos_offset=0)
block_2 = Block(uart=servo_uart, motor_id=9, pos_offset=0)
arm = Arm(uart=servo_uart, motor_id=10, pos_offset=0)

def set_error_led(on):
    error_led.value(0 if on else 1)  # active-low
