"""Example of RS485 gated FTM operation."""

import asyncio
import logging

from scietex.hal.serial import (
    ModbusSerialConnectionConfig,
    SerialConnectionConfig,
    VirtualSerialNetwork,
)
from scietex.hal.serial.utilities.serial_port_finder import find_rs485

from scietex.hal.qcm.base.data import Material
from scietex.hal.qcm.scietex import FtmOne


# pylint: disable=too-many-locals,too-many-statements
async def main(
    modbus_config: ModbusSerialConnectionConfig,
    address: int,
):
    """Main coroutine."""
    ftm = FtmOne(modbus_config, address=address, label="Scietex FTM")
    orig_baudrate = await ftm.get_baudrate()
    orig_address = await ftm.get_address()
    print(f"BR: {orig_baudrate}, ADDR: {orig_address}")

    await ftm.start_measurement(reset=True)
    for i in range(5):
        print()
        print(i)
        data = await ftm.read_registers(2000, count=21)
        print("ZZZZZZZ")
        print(data)
        print("ZZZZZZZ")

        print("YYYYYYY")
        data = await ftm.read_registers(2008, count=10)
        print(data)
        data = await ftm.read_registers(2018, count=7)
        print(data)
        print("YYYYYYY")
        parameters = await ftm.read_parameters()
        print(parameters)
        print("======")
        print()
        # frequency = await ftm.get_frequency()
        # counter = await ftm.get_counter()
        # print(f"{i:02d}) f={frequency}, CNT={counter}")
        # thickness = await ftm.get_thickness()
        # rate = await ftm.get_rate()
        # print(f"    Thickness={thickness} A, rate={rate} A/s")
        # if i == 2:
        #     print("Reset thickness")
        #     await ftm.reset_thickness()
    await ftm.stop_measurement()
    # parameters = await ftm.read_parameters()
    # print(f"Parameters: {parameters}")
    # data = await ftm.read_data()
    # print(f"Parameters: {data}")
    material = await ftm.get_material()
    print(f"Material: {material}")
    await ftm.set_material(Material(density=7.2, z_ratio=0.31))
    material = await ftm.get_material()
    print(f"Material: {material}")


if __name__ == "__main__":
    logger = logging.getLogger()
    vsn = VirtualSerialNetwork(
        virtual_ports_num=0, external_ports=None, loopback=False, logger=logger
    )
    vsn.start()
    rs485_ports = find_rs485()
    if rs485_ports:
        vsn.add([SerialConnectionConfig(port=rs485_ports[0], baudrate=19200, timeout=1.5)])
    else:
        print("No RS485 ports found.")
    vp = vsn.create(1)
    print(vp)
    connection_config = ModbusSerialConnectionConfig(port=vp[0], baudrate=19200, timeout=1)
    asyncio.run(main(connection_config, address=1))

    vsn.stop()
