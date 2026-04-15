from micropython import const
from machine import Pin, UART
from microharp.device import HarpDevice
from microharp.type import HarpTypes
from microharp.register import ReadWriteReg, ReadOnlyReg
from microharp.event import LooseEvent
from shelter import Platform
from register import PlatformReg
from utility import WaitAny


class MyDevice(HarpDevice):
    """My Harp device."""

    R_OP_H1 = const(15)
    R_OP_H2 = const(16)
    R_OP_H3 = const(17)
    R_OP_D1 = const(18)
    R_OP_D2 = const(19)
    R_OP_D3 = const(20)
    R_ACK_H1 = const(21)
    R_ACK_H2 = const(22)
    R_ACK_H3 = const(23)
    R_ACK_D1 = const(24)
    R_ACK_D2 = const(25)
    R_ACK_D3 = const(26)
    whoAmI = const(0x1234)

    def __init__(
        self,
        led,
        clock,
        monitor=None,
    ):
        """Constructor.

        Connects the logical device to its physical interfaces, creates the register map.
        """
        super().__init__(led, clock, monitor=monitor, txqlen=511)
        uart = UART(0, baudrate=1_000_000, tx=Pin(16), rx=Pin(17))
        self.h1 = Platform(uart, id=3)
        self.h2 = Platform(uart, id=5)
        self.h3 = Platform(uart, id=7)
        self.d1 = Platform(uart, id=2)
        self.d2 = Platform(uart, id=4)
        self.d3 = Platform(uart, id=6)
        registers = {
            HarpDevice.R_DEVICE_NAME: ReadWriteReg(HarpTypes.U8, tuple(b"Feeder V2")),
            HarpDevice.R_WHO_AM_I: ReadOnlyReg(HarpTypes.U16, (self.whoAmI,)),
            HarpDevice.R_HW_VERSION_H: ReadOnlyReg(HarpTypes.U8, (2,)),
            HarpDevice.R_HW_VERSION_L: ReadOnlyReg(HarpTypes.U8, (0,)),
            HarpDevice.R_FW_VERSION_H: ReadOnlyReg(HarpTypes.U8, (1,)),
            HarpDevice.R_FW_VERSION_L: ReadOnlyReg(HarpTypes.U8, (0,)),
            self.R_OP_H1: PlatformReg(HarpTypes.U8, self.h1),
            self.R_OP_H2: PlatformReg(HarpTypes.U8, self.h2),
            self.R_OP_H3: PlatformReg(HarpTypes.U8, self.h3),
            self.R_OP_D1: PlatformReg(HarpTypes.U8, self.d1),
            self.R_OP_D2: PlatformReg(HarpTypes.U8, self.d2),
            self.R_OP_D3: PlatformReg(HarpTypes.U8, self.d3),
            self.R_ACK_H1: ReadOnlyReg(HarpTypes.U8, (self.h1.status,)),
            self.R_ACK_H2: ReadOnlyReg(HarpTypes.U8, (self.h2.status,)),
            self.R_ACK_H3: ReadOnlyReg(HarpTypes.U8, (self.h3.status,)),
            self.R_ACK_D1: ReadOnlyReg(HarpTypes.U8, (self.d1.status,)),
            self.R_ACK_D2: ReadOnlyReg(HarpTypes.U8, (self.d2.status,)),
            self.R_ACK_D3: ReadOnlyReg(HarpTypes.U8, (self.d3.status,)),
        }
        self.registers.update(registers)

        self.h1Event = LooseEvent(self.R_ACK_H1, self.registers[self.R_ACK_H1], self.clock, self.txMessages)
        self.h2Event = LooseEvent(self.R_ACK_H2, self.registers[self.R_ACK_H2], self.clock, self.txMessages)
        self.h3Event = LooseEvent(self.R_ACK_H3, self.registers[self.R_ACK_H3], self.clock, self.txMessages)
        self.d1Event = LooseEvent(self.R_ACK_D1, self.registers[self.R_ACK_D1], self.clock, self.txMessages)
        self.d2Event = LooseEvent(self.R_ACK_D2, self.registers[self.R_ACK_D2], self.clock, self.txMessages)
        self.d3Event = LooseEvent(self.R_ACK_D3, self.registers[self.R_ACK_D3], self.clock, self.txMessages)

        self.events.extend([self.h1Event, self.h2Event, self.h3Event, self.d1Event, self.d2Event, self.d3Event])

        self.tasks.append(self.status_task())

    async def status_task(self):
        motors = [self.h1, self.h2, self.h3, self.d1, self.d2, self.d3]
        events = [self.h1Event, self.h2Event, self.h3Event, self.d1Event, self.d2Event, self.d3Event]
        while True:
            evt = await WaitAny(
                (
                    self.h1.isr,
                    self.h2.isr,
                    self.h3.isr,
                    self.d1.isr,
                    self.d2.isr,
                    self.d3.isr,
                )
            ).wait()

            for index, m in enumerate(motors):
                if evt is m.isr:
                    events[index].register.value = (m.status,)
                    events[index].callback()
                    if evt:
                        evt.clear()
