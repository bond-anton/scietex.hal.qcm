"""Example of RS485 gated FTM operation."""

import argparse
import asyncio

from scietex.hal.serial import ModbusSerialConnectionConfig
from scietex.hal.serial.utilities.serial_port_finder import find_rs485

from scietex.hal.qcm.base.data import Material
from scietex.hal.qcm.base.rs485 import RS485GatedFTM
from scietex.hal.qcm.cyky import TM106B
from scietex.hal.qcm.scietex import FtmOne


async def main(
    ftm_cls: type[RS485GatedFTM],
    modbus_config: ModbusSerialConnectionConfig,
    address: int,
):
    """Main coroutine."""
    ftm = ftm_cls(modbus_config, address=address, label="Scietex FTM")
    orig_baudrate = await ftm.get_baudrate()
    orig_address = await ftm.get_address()
    print(f"BR: {orig_baudrate}, ADDR: {orig_address}")
    """
    The baudrate is stored immediately but applied only after a device restart.
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
    """
    # await ftm.set_averaging(0)
    # await asyncio.sleep(1)
    await ftm.start_measurement(reset=True)
    for i in range(10):
        data = await ftm.read_registers(2000, count=21)
        print("ZZZZZZZ")
        print(data)
        print("ZZZZZZZ")
        parameters = await ftm.read_parameters()
        print(f"Parameters: {parameters}")
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
    parser = argparse.ArgumentParser(description="Exercise a RS485 gated FTM.")
    parser.add_argument(
        "--model", choices=["TM106B", "FtmOne"], default="TM106B", help="FTM model."
    )
    parser.add_argument(
        "--port", default=None, help="Serial port; defaults to the first RS485 port."
    )
    parser.add_argument("--address", type=int, default=3, help="RS485 address.")
    parser.add_argument("--baudrate", type=int, default=9600, help="RS485 baudrate.")
    args = parser.parse_args()

    ftm_models = {"TM106B": TM106B, "FtmOne": FtmOne}
    port = args.port or next(iter(find_rs485()), None)
    if port is not None:
        connection_config = ModbusSerialConnectionConfig(
            port=port, baudrate=args.baudrate, timeout=0.5
        )
        asyncio.run(main(ftm_models[args.model], connection_config, address=args.address))
    else:
        print("No RS485 ports found.")
