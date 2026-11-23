"""Harp application registers for the shelter motors.

On startup all motors are homed concurrently (see `attach`).

Each motor from `hardware` gets four registers, with the addresses taken
from `config`:

    ADDR_POS_*    (U8, write-only)         : target step, 0..255.  Writing
                                             starts a move to that position.
    ADDR_STATUS_* (U8, read-only + event)  : motor state (IDLE/UP/DOWN/
                                             MOVING/ERROR).  Every state
                                             change emits a Harp EVENT.
    ADDR_TRQ_*    (U8, read-write)         : torque limit.  Writes clamp to
                                             the motor's maximum; reads query
                                             the servo.
    ADDR_SPD_*    (U8, read-write)         : profile velocity.  Writes clamp
                                             to the motor's maximum; reads
                                             query the servo.
"""

from microharp import EVENT, PT_U8, READ_ONLY, READ_WRITE, WRITE_ONLY
from microharp.device import HarpDevice
from microharp.registers import OP_OP_MODE_ACTIVE, OP_OP_MODE_MASK, R_OPERATION_CONTROL

import asyncio

import config as cfg
from hardware import house_1, house_2, house_3, door_1, door_2, door_3, block_1, block_2, arm

# One row per motor: (motor, position, status, torque, speed register, name).
_MOTOR_MAP = (
    (house_1, cfg.ADDR_POS_HOUSE_1, cfg.ADDR_STATUS_HOUSE_1, cfg.ADDR_TRQ_HOUSE_1, cfg.ADDR_SPD_HOUSE_1, "House1"),
    (house_2, cfg.ADDR_POS_HOUSE_2, cfg.ADDR_STATUS_HOUSE_2, cfg.ADDR_TRQ_HOUSE_2, cfg.ADDR_SPD_HOUSE_2, "House2"),
    (house_3, cfg.ADDR_POS_HOUSE_3, cfg.ADDR_STATUS_HOUSE_3, cfg.ADDR_TRQ_HOUSE_3, cfg.ADDR_SPD_HOUSE_3, "House3"),
    (door_1, cfg.ADDR_POS_DOOR_1, cfg.ADDR_STATUS_DOOR_1, cfg.ADDR_TRQ_DOOR_1, cfg.ADDR_SPD_DOOR_1, "Door1"),
    (door_2, cfg.ADDR_POS_DOOR_2, cfg.ADDR_STATUS_DOOR_2, cfg.ADDR_TRQ_DOOR_2, cfg.ADDR_SPD_DOOR_2, "Door2"),
    (door_3, cfg.ADDR_POS_DOOR_3, cfg.ADDR_STATUS_DOOR_3, cfg.ADDR_TRQ_DOOR_3, cfg.ADDR_SPD_DOOR_3, "Door3"),
    (block_1, cfg.ADDR_POS_BLOCK_1, cfg.ADDR_STATUS_BLOCK_1, cfg.ADDR_TRQ_BLOCK_1, cfg.ADDR_SPD_BLOCK_1, "Block1"),
    (block_2, cfg.ADDR_POS_BLOCK_2, cfg.ADDR_STATUS_BLOCK_2, cfg.ADDR_TRQ_BLOCK_2, cfg.ADDR_SPD_BLOCK_2, "Block2"),
    (arm, cfg.ADDR_POS_ARM, cfg.ADDR_STATUS_ARM, cfg.ADDR_TRQ_ARM, cfg.ADDR_SPD_ARM, "Arm"),
)


def _clamp_u8(val):
    return 0 if val < 0 else 255 if val > 255 else val


def attach(device: HarpDevice):
    op_reg = device.bank.get(R_OPERATION_CONTROL)

    def active():
        """Harp events are only allowed in Active mode."""
        return op_reg is not None and (op_reg.storage[0] & OP_OP_MODE_MASK) == OP_OP_MODE_ACTIVE

    for motor, pos_addr, status_addr, trq_addr, spd_addr, name in _MOTOR_MAP:
        _attach_motor(device, active, motor, pos_addr, status_addr, trq_addr, spd_addr, name)

    # Home all motors concurrently once the event loop is up, so the device
    # can answer Harp requests while homing.  A canceled calibration does
    # not prevent the remaining motors from continuing.

        motor.start_calibration()

    # @device.task
    # async def _calibrate_on_init():
    #     async def _calibrate(motor):
    #         try:
    #             await motor.start_calibration()
    #         except asyncio.CancelledError:
    #             pass  # a host command replaced this calibration

    #     await asyncio.gather(*(_calibrate(row[0]) for row in _MOTOR_MAP))


def _attach_motor(device, active, motor, pos_addr, status_addr, trq_addr, spd_addr, name):
    # Position command: writing a TargetPosition step (0..255) starts a move.
    async def _pos_write(reg, payload, _motor=motor):
        reg.storage[0] = payload[0]
        _motor.move(payload[0])
        return None

    device.add_register(pos_addr, PT_U8, access=WRITE_ONLY, on_write=_pos_write, name="Pos" + name)

    # Status: refreshed just-in-time on READ, emitted as an EVENT on change.
    async def _status_read(reg, _motor=motor):
        reg.storage[0] = _motor.status

    status_reg = device.add_register(
        status_addr, PT_U8, access=READ_ONLY | EVENT, on_read=_status_read, name="Status" + name
    )
    status_reg.storage[0] = motor.status

    # Torque limit and profile velocity: READ queries the servo (serving
    # the last known value if it is silent), WRITE applies the new value
    # clamped by the motor's setter.  A servo comms failure on a write
    # answers with a Harp WRITE error.
    async def _trq_write(reg, payload, _motor=motor):
        try:
            _motor.torque = payload[0]
            reg.storage[0] = _clamp_u8(_motor.torque)
        except Exception:
            return 1  # non-None -> WRITE_ERROR reply
        return None

    async def _trq_read(reg, _motor=motor):
        try:
            reg.storage[0] = _clamp_u8(_motor.torque)
        except Exception:
            pass  # servo silent: serve the last known value

    trq_reg = device.add_register(
        trq_addr, PT_U8, access=READ_WRITE, on_read=_trq_read, on_write=_trq_write, name="Trq" + name
    )

    async def _spd_write(reg, payload, _motor=motor):
        try:
            _motor.speed = payload[0]
            reg.storage[0] = _clamp_u8(_motor.speed)
        except Exception:
            return 1  # non-None -> WRITE_ERROR reply
        return None

    async def _spd_read(reg, _motor=motor):
        try:
            reg.storage[0] = _clamp_u8(_motor.speed)
        except Exception:
            pass  # servo silent: serve the last known value

    spd_reg = device.add_register(
        spd_addr, PT_U8, access=READ_WRITE, on_read=_spd_read, on_write=_spd_write, name="Spd" + name
    )

    # Seed with the servo's current values; it may be absent at boot.
    try:
        trq_reg.storage[0] = _clamp_u8(motor.torque)
        spd_reg.storage[0] = _clamp_u8(motor.speed)
    except Exception:
        pass

    # The motor sets `isr` on every state-machine step; mirror the new
    # status into the register and emit an EVENT while Active.
    async def _watch(_motor=motor, _reg=status_reg, _addr=status_addr):
        last = _reg.storage[0]
        while True:
            await _motor.isr.wait()
            _motor.isr.clear()
            status = _motor.status
            _reg.storage[0] = status
            if status != last:
                last = status
                if active():
                    await device.emit(_addr, status)

    device.task(_watch)

