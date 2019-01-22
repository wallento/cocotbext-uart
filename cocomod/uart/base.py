from cocotb import SimLog, coroutine
from cocotb.drivers import Driver
from cocotb.monitors import Monitor
from cocotb.result import TestError
from cocotb.triggers import Timer, RisingEdge, FallingEdge


class UARTModule(Driver, Monitor):
    _signals = ["tx", "rx", "ctsn", "rtsn"]

    def __init__(self, freq, baud, clk, signals):
        self.log = SimLog("cocomod.uart.{}".format(self.__class__.__name__))

        self.clk = clk
        self.divisor = round(freq/baud)
        self.tx = signals["tx"]
        self.tx <= 1
        self.rx = signals["rx"]

        Driver.__init__(self)
        Monitor.__init__(self)

    @coroutine
    def _driver_send(self, transaction, sync=True, **kwargs):
        self.tx <= 0
        for i in range(self.divisor):
            yield (RisingEdge(self.clk))
        for b in range(8):
            self.tx <= ((transaction >> b) & 0x1)
            for i in range(self.divisor):
                yield (RisingEdge(self.clk))
        self.tx <= 1
        for i in range(self.divisor):
            yield (RisingEdge(self.clk))

    @coroutine
    def _monitor_recv(self):
        while True:
            data = 0
            yield FallingEdge(self.rx)
            for i in range(round(self.divisor/2)):
                yield (RisingEdge(self.clk))
            if self.rx != 0:
                raise TestError("start bit error")
            for b in range(8):
                for i in range(self.divisor):
                    yield (RisingEdge(self.clk))
                if self.rx == 1:
                    data = data | (1 << b)
            for i in range(self.divisor):
                yield (RisingEdge(self.clk))
            self._recv(data)

