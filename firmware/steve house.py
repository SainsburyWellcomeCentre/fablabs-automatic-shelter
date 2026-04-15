from machine import Pin, UART
import asyncio
from micropython import const
from shelter import Platform
from utility import WaitAny
from collections import deque
import sys

UART_BAUD = 1_000_000  # Baud rate for hardware UART
UART_NUM = 0  # Use UART0
INDICATOR_PIN = 25  # GPIO for indicator LED
LIMITER_PIN = 28  # GPIO for limiter


led = Pin(INDICATOR_PIN, Pin.OUT, value=0)  # Indicator LED

uart = UART(0, baudrate=1_000_000, tx=Pin(16), rx=Pin(17))  # Adjust pins if needed

h1 = Platform(uart, id=3)
h2 = Platform(uart, id=5)
h3 = Platform(uart, id=7)
d1 = Platform(uart, id=2)
d2 = Platform(uart, id=4)
d3 = Platform(uart, id=6)

motors = [h1, h2, h3, d1, d2, d3]


TX_LEN = 128
RX_LEN = 128


async def event_monitor(txMessages: deque):
    while True:

        evt = await WaitAny(
            (
                h1.isr,
                h2.isr,
                h3.isr,
                d1.isr,
                d2.isr,
                d3.isr,
            )
        ).wait()

        for index, m in enumerate(motors):
            if evt is m.isr:
                txMessages.append(index)
                txMessages.append(m.status)

        if evt:
            evt.clear()


async def transceiver(txMessages: deque, rxMessages: deque):

    while True:
        # Send messages
        while txMessages:
            message = txMessages.popleft()
            sys.stdout.write(bytearray([message]))

        await asyncio.sleep(0)


async def processor(rxMessages: deque):
    while True:
        for m in motors:
            m.raise_up()
            await asyncio.sleep(3.5)
        for idx in range(3):
            motors[idx + 3].lower_down()
            await asyncio.sleep(3.5)
        for idx in range(3):
            motors[idx].lower_down()
            await asyncio.sleep(3.5)


async def main():

    txMessages = deque(bytearray(), TX_LEN)
    rxMessages = deque(bytearray(), RX_LEN)

    monitor_task = asyncio.create_task(event_monitor(txMessages))
    processor_task = asyncio.create_task(processor(rxMessages))
    transceiver_task = asyncio.create_task(transceiver(txMessages, rxMessages))

    await asyncio.gather(monitor_task, processor_task, transceiver_task)


asyncio.run(main())
