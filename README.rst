Cocotb UART Modules
===================

Install
-------

From Github
^^^^^^^^^^^

* Clone the repository::

    $ git clone https://github.com/wallento/cocotbext-uart.git

* Then install it with pip::

    $ python -m pip install -e cocotbext-uart

From pip global
^^^^^^^^^^^^^^^

To install it with pip published globally simply use pip install as usual::

    $ python -m pip install cocotbext-uart

How to use it
-------------

Sending value
^^^^^^^^^^^^^

Here an example to send data with uart protocol to a DUT module with only input
Rx uart pin named RxBit

First, import following :

    from cocotbext.uart import UARTConfig
    from cocotbext.uart import UARTModule
    from cocotbext.uart import UARTSignals

Then instanciate the config class, NameTuple signals and the module:

    class MyBench(object):
        def __init__(self, dut):
            self._clock = Clock(dut.clk, 20, units="ns") # Create a 50Mhz clock
            self._uart_config = UARTConfig(baud=19200)
            self._uartsig = UARTSignals(tx = dut.RxBit,
                                        rx = dut.RxBit, # loop tx->rx
                                        ctsn = None,
                                        rtsn = None)
            self._uart_drv = UARTModule(config=self._uart_config,
                            signals=self._uartsig,
                            clk=self._clock)

Once all declarations/instanciations done, send a value in test function:

    @cocotb.test()
    async def test_simple(dut):
        tmb = TestMyBench(dut)
        tmb.log.info("Simple uart test")
        await tmb._uart_drv.send(0x42)
        await Timer(20, units="us")
        tmb.log.info("End of Simple uart test")

Receiving value
^^^^^^^^^^^^^^^

TODO
