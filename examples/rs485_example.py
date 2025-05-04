"""Example of RS485 gated FTM operation."""

import asyncio
from typing import Type

from scietex.hal.serial import ModbusSerialConnectionConfig
from scietex.hal.serial.utilities.serial_port_finder import find_rs485

from scietex.hal.qcm.base.rs485 import RS485GatedFTM

from scietex.hal.qcm.base.data import Material
from scietex.hal.qcm.cyky import TM106B
from scietex.hal.qcm.scietex import FtmOne


# pylint: disable=too-many-locals,too-many-statements
async def main(
    ftm_cls: Type[RS485GatedFTM], modbus_config: ModbusSerialConnectionConfig, address: int
):
    """Main coroutine."""
    ftm = ftm_cls(modbus_config, address=address, label="Scietex FTM")
    orig_baudrate = await ftm.get_baudrate()
    orig_address = await ftm.get_address()
    print(f"BR: {orig_baudrate}, ADDR: {orig_address}")
    new_baudrate = 9600
    print(f"Changing baudrate to {new_baudrate}")
    await ftm.set_baudrate(new_baudrate)
    baudrate = await ftm.get_baudrate()
    address = await ftm.get_address()
    print(f"BR: {baudrate}, ADDR: {address}")
    print(f"Changing baudrate back to {orig_baudrate}")
    await ftm.set_baudrate(orig_baudrate)
    baudrate = await ftm.get_baudrate()
    address = await ftm.get_address()
    print(f"BR: {baudrate}, ADDR: {address}")

    new_address = 123
    print(f"Changing address to {new_address}")
    await ftm.set_address(new_address)
    baudrate = await ftm.get_baudrate()
    address = await ftm.get_address()
    print(f"BR: {baudrate}, ADDR: {address}")
    print(f"Changing address back to {orig_address}")
    await ftm.set_address(orig_address)
    baudrate = await ftm.get_baudrate()
    address = await ftm.get_address()
    print(f"BR: {baudrate}, ADDR: {address}")

    vendor = await ftm.get_vendor()
    product_name = await ftm.get_product_name()
    version = await ftm.get_version()
    serial_number = await ftm.get_serial_number()
    print(f"FTM: {vendor} {product_name}, VER. {version}, SN: {serial_number}")

    gate_time = await ftm.get_gate_time()
    print(f"Gate time: {gate_time} ms")
    await ftm.set_gate_time(250)
    gate_time = await ftm.get_gate_time()
    print(f"Gate time: {gate_time} ms")
    await ftm.set_gate_time(1000)

    averaging_window = await ftm.get_averaging()
    averaging_progress = await ftm.get_averaging_progress()
    print(f"Averaging: {averaging_progress}/{averaging_window}")
    await ftm.set_averaging(10)
    averaging_window = await ftm.get_averaging()
    averaging_progress = await ftm.get_averaging_progress()
    print(f"Averaging: {averaging_progress}/{averaging_window}")

    # await ftm.set_averaging(0)
    # await asyncio.sleep(1)
    await ftm.start_measurement(reset=True)
    for i in range(10):
        frequency = await ftm.get_frequency()
        counter = await ftm.get_counter()
        print(f"{i:02d}) f={frequency}, CNT={counter}")
        thickness = await ftm.get_thickness()
        rate = await ftm.get_rate()
        print(f"    Thickness={thickness} A, rate={rate} A/s")
        if i == 6:
            print("Reset thickness")
            await ftm.reset_thickness()
    await ftm.stop_measurement()
    parameters = await ftm.read_parameters()
    print(f"Parameters: {parameters}")
    data = await ftm.read_data()
    print(f"Parameters: {data}")
    material = await ftm.get_material()
    print(f"Material: {material}")
    await ftm.set_material(Material(density=7.2, z_ratio=0.31))
    material = await ftm.get_material()
    print(f"Material: {material}")


if __name__ == "__main__":
    ftm_models = [FtmOne, TM106B]
    rs485_ports = find_rs485()
    if rs485_ports:
        connection_config = ModbusSerialConnectionConfig(
            port=rs485_ports[0], baudrate=19200, timeout=0.5
        )
        asyncio.run(main(ftm_models[0], connection_config, address=1))
    else:
        print("No RS485 ports found.")
