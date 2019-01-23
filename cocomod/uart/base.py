from collections import namedtuple

from cocotb import SimLog, coroutine
from cocotb.drivers import Driver
from cocotb.monitors import Monitor
from cocotb.result import TestError
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from enum import Enum

from cocotb.utils import get_time_from_sim_steps, get_sim_steps

UARTParity = Enum("UARTParity", "NONE ODD EVEN")
UARTFlowControl = Enum("UARTFlowControl", "NONE HARDWARE SOFTWARE")

UARTSignals = namedtuple("UARTSignals", ['tx', 'rx', 'ctsn', 'rtsn'])
UARTSignals.__new__.__defaults__ = (None, None)


def parity(data, bits, parity):
    p = 0
    for i in range(bits):
        if (data >> i) & 0x1:
            p = 1-p
    if parity == UARTParity.EVEN:
        return p
    else:
        return 1-p


class UARTConfig(object):
    def __init__(self, *, bits=8, parity=UARTParity.NONE, stopbits=1, baud=115200, flow_control=UARTFlowControl.NONE):
        self.bits = bits
        self.parity = parity
        self.stopbits = stopbits
        self.baud = baud
        self.flow_control = flow_control

    def __setattr__(self, key, value):
        if key == "bits":
            if int(value) not in range(5, 10):
                raise TypeError("bits must be an integer in the range 5 to 9")
        elif key == "parity":
            if not isinstance(value, UARTParity):
                raise TypeError("parity must be instance of UARTParity")
        elif key == "stopbits":
            if int(value) not in range(1, 3):
                raise TypeError("stop bits must be either 1 or 2")
        elif key == "baud":
            value = int(value)
        elif key == "flow_control":
            if not isinstance(value, UARTFlowControl):
                raise TypeError("parity must be instance of UARTFlowControl")
        self.__dict__[key] = value


class UARTModule(Driver, Monitor):
    def __init__(self, config, signals, clk, *, clk_freq=None):
        self.log = SimLog("cocomod.uart.{}".format(self.__class__.__name__))

        self.config = config
        self.clk = clk.signal
        if clk_freq is None:
            clk_freq = 1 / get_time_from_sim_steps(clk.period, "sec")
        self.divisor = round(clk_freq/config.baud)
        self.duration = clk.period * self.divisor
        self.tx = signals.tx
        self.rx = signals.rx
        self.ctsn = signals.ctsn
        self.rtsn = signals.rtsn

        if config.flow_control == UARTFlowControl.HARDWARE and self.ctsn is None:
            raise RuntimeError("HARDWARE flow control selected and no CTS signal")
        if config.flow_control == UARTFlowControl.HARDWARE and self.rtsn is None:
            raise RuntimeError("HARDWARE flow control selected and no RTS signal")

        self.tx <= 1
        if self.ctsn is not None:
            self.ctsn <= 1

        Driver.__init__(self)
        Monitor.__init__(self)

    @coroutine
    def _driver_send(self, transaction, sync=True, **kwargs):
        if self.config.flow_control == UARTFlowControl.HARDWARE and self.rtsn == 1:
            yield FallingEdge(self.rtsn)

        if sync:
            yield (RisingEdge(self.clk))

        # Start bit
        self.tx <= 0
        yield Timer(self.duration)

        # Bits
        for b in range(self.config.bits):
            self.tx <= ((transaction >> b) & 0x1)
            yield Timer(self.duration)

        # Parity
        if self.config.parity != UARTParity.NONE:
            self.tx <= parity(transaction, self.config.bits, self.config.parity)
            yield Timer(self.duration)

        # Stop bit(s)
        for b in range(self.config.stopbits):
            self.tx <= 1
            yield Timer(self.duration)

    @coroutine
    def _monitor_recv(self):
        while True:
            data = 0

            if self.config.flow_control == UARTFlowControl.HARDWARE:
                self.ctsn <= 0

            # Wait for start of character
            yield FallingEdge(self.rx)

            # Sample on the center of the start bit
            yield Timer(self.duration/2)

            # Malformed start bit
            if self.rx != 0:
                raise TestError("start bit error")

            # Sample all bits
            for b in range(self.config.bits):
                yield Timer(self.duration)
                if self.rx == 1:
                    data = data | (1 << b)

            # Parity
            if self.config.parity != UARTParity.NONE:
                yield Timer(self.duration)
                if self.rx != parity(data, self.config.bits, self.config.parity):
                    raise TestError("parity error")

            # Stopbit(s)
            for b in range(self.config.stopbits):
                yield Timer(self.duration)
                if self.rx != 1:
                    raise TestError("stop bit error")

            if self.config.flow_control == UARTFlowControl.HARDWARE:
                self.ctsn <= 1

            self._recv(data)

