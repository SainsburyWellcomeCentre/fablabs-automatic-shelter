from dynamixel import Dynamixel, DynamixelModel
from micropython import const
from asyncio import Event
import asyncio
from machine import UART


IDLE = const(0x00)
UP = const(0x01)
DOWN = const(0x02)
MOVING = const(0x03)
ERROR = const(0xFF)

TOLERANCE = const(20)


# Homing: the motor is at the end stop when the position changes by less
# than TOLERANCE from the anchor sample for CAL_STABLE_COUNT samples in a
# row.  CAL_TIMEOUT_S bounds the whole search.
CAL_STABLE_COUNT = const(5)
CAL_SAMPLE_MS = const(50)
CAL_SETTLE_MS = const(200)
CAL_TIMEOUT_S = const(30)
CAL_SPEED = const(200)



class Motor(Dynamixel):

    def __init__(self, uart: UART, motor_model: int, motor_id: int, default_vel, default_trq, max_vel, max_trq, pos_offset, length):

        super().__init__(uart, model=motor_model, id=motor_id)

        self.home_pos = 0
        self.target_pos = 0
        self.max_pos = 0
        self.pos_scale = length / 255
        self.pos_offset = pos_offset
        self.length = length
        self._ismoving = False
        self._isup = False
        self._isdown = False
        self._iscalibrating = False
        self._iserror = False

        self.isr = Event()
        self._task = None

        # The servo may be absent or unpowered. The device must still start,
        # so a failure here only sets the ERROR state. Calibrate retries.
        try:
            self._setup_servo(default_vel, default_trq, max_vel, max_trq)
        except Exception:
            self._iserror = True

    def _setup_servo(self, vel, trq, max_vel, max_trq):
        """Apply the operating mode and the default limits.

        Raises if the servo does not answer.
        """
        self.torque_enabled = False
        self.operating_mode = 5  # current control mode
        self.home_pos = self.present_position - self.length
        self.target_pos = self.home_pos
        self.max_vel = max_vel
        self.max_trq = max_trq
        self.speed = vel
        self.torque = trq

    @property
    def status(self) -> int:
        if self._iserror:
            return ERROR
        elif self._ismoving:
            return MOVING
        elif self._isup:
            return UP
        elif self._isdown:
            return DOWN
        return IDLE

    @property
    def torque(self):
        return self.current_limit

    @torque.setter
    def torque(self, val):
        val = max(0, min(val, self.max_trq))
        temp = self.torque_enabled
        self.torque_enabled = False
        self.current_limit = val
        # Do not switch the motor on if the host disabled it.
        self.torque_enabled = temp

    @property
    def speed(self):
        return self.profile_velocity

    @speed.setter
    def speed(self, vel):
        # Profile Velocity is in RAM, so it can be written with torque on.
        self.profile_velocity = max(0, min(vel, self.max_vel))

    @property
    def position(self) -> int:
        """Where the gate is now, on the TargetPosition scale of 0 to 255.

        Raises if the servo does not answer.
        """
        return self.scale_position(self.present_position, self.home_pos)

    def lower_down(self):
        if self.status != DOWN:
            self.move(0)

    def raise_up(self):
        if self.status != UP:
            self.move(255)

    def move(self, pos):
        pos = round(self.pos_scale * pos) + self.home_pos
        pos = min(pos, self.max_pos)
        pos = max(pos, self.home_pos)
        self.target_pos = pos
        self._start(self._run())

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
            try:
                self.goal_position = self.present_position
            except Exception:
                self._iserror = True
            self._ismoving = False
            self.isr.set()

    def start_calibration(self):
        return self._start(self.calibrate())

    def _start(self, coro):
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(coro)
        return self._task

    async def _run(self):
        self._isup = False
        self._isdown = False
        try:
            self._enable()

            if self.target_pos > self.present_position:
                while self.present_position < self.target_pos - TOLERANCE:
                    await asyncio.sleep_ms(50)
            else:
                while self.present_position > self.target_pos + TOLERANCE:
                    await asyncio.sleep_ms(50)

            if self.target_pos == self.home_pos:
                await asyncio.sleep_ms(100)
                self.torque_enabled = False
                await asyncio.sleep_ms(500)
                self._isdown = True
            elif self.target_pos == self.max_pos:
                self._isup = True
        except Exception:
            # A servo comms error. A CancelledError passes through.
            self._iserror = True
        finally:
            self._disable()

    def _disable(self):
        self._ismoving = False
        self.isr.set()

    def _enable(self):
        self.torque_enabled = True
        self.goal_extend_position = self.target_pos
        self._ismoving = True
        self.isr.set()

    async def calibrate(self):
        """Drive the gate to the lower end stop and record it as home.

        Runs as a task, so the device stays on the bus while homing.
        On timeout or a servo error the gate enters the ERROR state.

        Homing drives the gate into the end stop, so `_setup_servo` puts the
        safe default speed and torque on the servo. The values the host set
        are read first and put back at the end, so a calibration does not
        change them.
        """
        self._iserror = False
        self._isup = False
        self._isdown = False
        try:
            temp_spd = self.speed
            self.speed = CAL_SPEED
            self._enable()
            await asyncio.wait_for(self._find_home(), CAL_TIMEOUT_S)
            self.torque_enabled = False
            await asyncio.sleep_ms(500)
            self.home_pos = self.present_position + self.pos_offset
            self.max_pos = self.home_pos + self.length - self.pos_offset
            self.target_pos = self.home_pos
            # Release the motor so it stops pressing into the end stop,
            # like the home-position branch of _run().
            self._isdown = True
            self.speed = temp_spd
            self._disable()
        except Exception:
            # asyncio.TimeoutError, or a servo comms error. A CancelledError
            # from move() or stop() is a BaseException and passes through.
            self._iserror = True
            try:
                self.torque_enabled = False
            except Exception:
                pass
        finally:
            self._iscalibrating = False
            self.isr.set()

    async def _find_home(self):
        """Wait until the position stops changing: the end stop is reached.

        Compares against an anchor sample rather than the previous sample,
        so a slow steady creep (less than TOLERANCE per sample, as the
        Block motors produce at their default speed) still resets the
        stability count instead of passing as "stable".
        """
        await asyncio.sleep_ms(CAL_SETTLE_MS)
        anchor = self.present_position
        stable = 0
        while stable <= CAL_STABLE_COUNT:
            await asyncio.sleep_ms(CAL_SAMPLE_MS)
            pos = self.present_position
            if abs(pos - anchor) < TOLERANCE:
                stable += 1
            else:
                stable = 0
                anchor = pos

    def scale_position(self, encoder, home):
        
        """Turn a pair of encoder counts into a TargetPosition step, 0 to 255.

        The task reports Position and RawPosition from one servo read, so it needs
        the same scale the `position` property uses.
        """
        pos = (encoder - home) // self.pos_scale
        return 0 if pos < 0 else 255 if pos > 255 else pos

class House(Motor):
    def __init__(self, uart: UART, motor_id: int, pos_offset: int):
        super().__init__(uart, DynamixelModel.XM430_W350, motor_id, default_vel=100, default_trq=64, max_vel=200, max_trq=100, pos_offset=pos_offset, length=8720)

class Door(Motor):
    def __init__(self, uart: UART, motor_id: int, pos_offset: int):
        super().__init__(uart, DynamixelModel.XM430_W350, motor_id, default_vel=100, default_trq=80, max_vel=200, max_trq=100, pos_offset=pos_offset, length=8720)

class Block(Motor):
    def __init__(self, uart: UART, motor_id: int, pos_offset: int):
        super().__init__(uart, DynamixelModel.XM430_W210, motor_id, default_vel=40, default_trq=85, max_vel=100, max_trq=100, pos_offset=pos_offset, length=530)

class Arm(Motor):
    def __init__(self, uart: UART, motor_id: int, pos_offset: int):
        super().__init__(uart, DynamixelModel.XM430_W210, motor_id, default_vel=7, default_trq=188, max_vel=20, max_trq=255, pos_offset=pos_offset, length=950)

    @property
    def torque(self):
        return self.current_limit >> 2

    @torque.setter
    def torque(self, val):
        val = max(0, min(val, self.max_trq))
        val = val << 2
        temp = self.torque_enabled
        self.torque_enabled = False
        self.current_limit = val
        # Do not switch the motor on if the host disabled it.
        self.torque_enabled = temp

