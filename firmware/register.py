from microharp.register import ReadWriteReg
from shelter import Platform


class PlatformReg(ReadWriteReg):
    """Read/write register with debug print."""

    def __init__(self, typ, device: Platform):
        super().__init__(typ)
        self.device = device

    def write(self, typ, value):
        if value == 0:
            self.device.lower_down()
        else:
            self.device.raise_up()
        self.value = (value,)
