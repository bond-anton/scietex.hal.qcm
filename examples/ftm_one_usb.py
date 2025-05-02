"""Example of RS485 gated FTM operation."""

# pylint: disable=duplicate-code

import asyncio
from typing import Type

from scietex.hal.serial import SerialConnectionConfig

from scietex.hal.qcm.base.serial import SerialGatedFTM

from scietex.hal.qcm.base.data import Material
from scietex.hal.qcm.scietex import FtmOneUSB, find_ftm_one_usb


# pylint: disable=too-many-locals,too-many-statements
async def main(ftm_cls: Type[SerialGatedFTM], serial_config: SerialConnectionConfig):
    """Main coroutine."""
    ftm = ftm_cls(serial_config, label="Scietex FTM", keep_connection=False)
    if isinstance(ftm, FtmOneUSB):
        await ftm.set_rs485_baudrate(9600)
        await ftm.set_rs485_address(3)
        baudrate = await ftm.get_rs485_baudrate()
        address = await ftm.get_rs485_address()
        print(f"BR: {baudrate}, ADDR: {address}")
        await ftm.set_rs485_baudrate(19200)
        await ftm.set_rs485_address(1)
        baudrate = await ftm.get_rs485_baudrate()
        address = await ftm.get_rs485_address()
        print(f"BR: {baudrate}, ADDR: {address}")
    ftm.pin = 1234
    vendor = await ftm.get_vendor()
    product_name = await ftm.get_product_name()
    version = await ftm.get_version()
    serial_number = await ftm.get_serial_number()
    print(f"FTM: {vendor} {product_name}, VER. {version}, SN: {serial_number}")
    if isinstance(ftm, FtmOneUSB):
        await ftm.set_serial_number(1)
    serial_number = await ftm.get_serial_number()
    print(f"FTM: {vendor} {product_name}, VER. {version}, SN: {serial_number}")

    mcu_f = await ftm.get_mcu_frequency()
    print(f"MCU f: {mcu_f} Hz.")

    await ftm.set_gate_time(500)
    gate_time = await ftm.get_gate_time()
    print(f"Gate time: {gate_time} ms")
    await ftm.set_gate_time(1000)
    gate_time = await ftm.get_gate_time()
    print(f"Gate time: {gate_time} ms")
    if isinstance(ftm, FtmOneUSB):
        prescaler_count = await ftm.get_gate_prescaler_count()
        print(prescaler_count)

    averaging_window = await ftm.get_averaging()
    averaging_progress = await ftm.get_averaging_progress()
    print(f"Averaging: {averaging_progress}/{averaging_window}")
    averaging_window = await ftm.set_averaging(5)
    print(f"Averaging window set to {averaging_window}")
    averaging_window = await ftm.get_averaging()
    averaging_progress = await ftm.get_averaging_progress()
    print(f"Averaging: {averaging_progress}/{averaging_window}")
    averaging_window = await ftm.set_averaging(3)
    print(f"Averaging window set to {averaging_window}")
    averaging_window = await ftm.get_averaging()
    averaging_progress = await ftm.get_averaging_progress()
    print(f"Averaging: {averaging_progress}/{averaging_window}")
    averaging_window = await ftm.set_averaging(10)
    print(f"Averaging window set to {averaging_window}")
    averaging_window = await ftm.get_averaging()
    averaging_progress = await ftm.get_averaging_progress()
    print(f"Averaging: {averaging_progress}/{averaging_window}")

    material = await ftm.get_material()
    print(f"Material: {material}")
    await ftm.set_material(Material(density=7.2, z_ratio=0.31))
    material = await ftm.get_material()
    print(f"Material: {material}")
    await ftm.set_ftm_scale(4.0)
    scale = await ftm.get_ftm_scale()
    print(f"Scale: {scale}")
    await ftm.set_ftm_scale(1.0)
    scale = await ftm.get_ftm_scale()
    print(f"Scale: {scale}")

    await ftm.set_target_um(0.1)
    target = await ftm.get_target_thickness()
    print(f"Target: {target} A")
    await ftm.set_target_nm(10)
    target = await ftm.get_target_thickness()
    print(f"Target: {target} A")

    averaging_window = await ftm.get_averaging()
    averaging_progress = await ftm.get_averaging_progress()
    print(f"\nAveraging: {averaging_progress}/{averaging_window}")
    frequency = await ftm.get_frequency()
    counter = await ftm.get_counter()
    print(f"f={frequency}, CNT={counter}")
    thickness = await ftm.get_thickness()
    rate = await ftm.get_rate()
    print(f"Thickness={thickness} A, rate={rate} A/s")

    await ftm.start_measurement(reset=True)

    for i in range(10):
        await asyncio.sleep(1)
        averaging_window = await ftm.get_averaging()
        averaging_progress = await ftm.get_averaging_progress()
        print(f"\nAveraging: {averaging_progress}/{averaging_window}")
        frequency = await ftm.get_frequency()
        counter = await ftm.get_counter()
        print(f"f={frequency}, CNT={counter}")
        thickness = await ftm.get_thickness()
        rate = await ftm.get_rate()
        print(f"Thickness={thickness} A, rate={rate} A/s")
        if i == 5:
            await ftm.reset_thickness()
            thickness = await ftm.get_thickness()
            rate = await ftm.get_rate()
            print(f"RESET Thickness={thickness} A, rate={rate} A/s")

    await ftm.stop_measurement()

    await asyncio.sleep(1)

    averaging_window = await ftm.get_averaging()
    averaging_progress = await ftm.get_averaging_progress()
    print(f"\nAveraging: {averaging_progress}/{averaging_window}")
    frequency = await ftm.get_frequency()
    counter = await ftm.get_counter()
    print(f"f={frequency}, CNT={counter}")
    thickness = await ftm.get_thickness()
    rate = await ftm.get_rate()
    print(f"Thickness={thickness} A, rate={rate} A/s")

    f_inst = await ftm.get_frequency_instant()
    print(f"f_inst: {f_inst} Hz.")


if __name__ == "__main__":
    ftm_models = [FtmOneUSB]
    ftm_one_serial_ports = find_ftm_one_usb()
    if ftm_one_serial_ports:
        connection_config = SerialConnectionConfig(
            port=ftm_one_serial_ports[0], baudrate=19200, timeout=0.5
        )
        asyncio.run(main(ftm_models[0], connection_config))
    else:
        print("No ftmONE device found.")
