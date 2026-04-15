from dynamixel import Dynamixel, DynamixelModel
import time
from micropython import const
from asyncio import Event
import asyncio


offset = const(8720)
torque_lim = const(55)
pwm_lim = const(300)
velocity_lim = const(100)
up = const(1)
down = const(0)
moving = const(2)
tolerance = const(20)


class Platform(Dynamixel):

    def __init__(self, uart, id):
        super().__init__(uart, model=DynamixelModel.XM430_W350, id=id)

        self.torque_enabled = False
        self.speed = pwm_lim
        self.operating_mode = 5  # current control mode
        self.home_pos = self.current_position - 10000
        self.torque = torque_lim
        self._calibrate_home()

        self.target_pos = self.home_pos
        self._ismoving = False
        self._isup = False
        self.isr = Event()
        self._task = None

    @property
    def status(self) -> int:
        temp = moving if self._ismoving else 0
        temp += up if self._isup else down
        return temp

    def lower_down(self):
        if self.status != down:
            self.target_pos = self.home_pos
            if self._task and not self._task.done():
                self._task.cancel()
            self._task = asyncio.create_task(self._run())

    def raise_up(self):
        if self.status != up:
            self.target_pos = self.home_pos + offset
            if self._task and not self._task.done():
                self._task.cancel()
            self._task = asyncio.create_task(self._run())

    def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
            self.goal_position = self.current_position
            self._ismoving = False
            self.isr.set()

    async def _run(self):
        self._enable()

        if self.target_pos > self.current_position:
            while self.current_position < self.target_pos - tolerance:
                await asyncio.sleep_ms(50)
        else:
            while self.current_position > self.target_pos + tolerance:
                await asyncio.sleep_ms(50)

        self._isup = True if self.target_pos == self.home_pos + offset else False

        self._disable()

    def _disable(self):
        self._ismoving = False
        self.isr.set()

    def _enable(self):
        self.goal_extend_position = self.target_pos
        self._ismoving = True
        self.isr.set()

    @property
    def torque(self):
        return self.current_limit

    @torque.setter
    def torque(self, vel):
        self.torque_enabled = False
        self.current_limit = vel
        self.torque_enabled = True

    @property
    def speed(self):
        return self.pwm_limit

    @speed.setter
    def speed(self, vel):
        self.pwm_limit = vel

    def _calibrate_home(self):
        self.torque_enabled = True
        self.goal_extend_position = self.home_pos
        last_pos = self.current_position
        time.sleep(0.2)
        conuter = 0
        while True:
            pos = self.current_position
            if abs(last_pos - pos) < 10:  # Check if the motor is close to the home position
                conuter += 1
            if conuter > 10:
                break
            last_pos = pos
            time.sleep(0.01)
        self.home_pos = self.current_position + 30  # Add a small offset to ensure the platform is fully lowered
        self.goal_position = self.home_pos
