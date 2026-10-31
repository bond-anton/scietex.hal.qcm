"""CYKY TM106B FTM over RS485."""

from logging import Logger

from scietex.hal.serial import ModbusSerialConnectionConfig

from ..base.data import GatedFTMCapabilities
from ..base.rs485 import RS485GatedFTM
from . import registers
from .protocol import TM106BProtocolMixin

TM106B_CAPABILITIES = GatedFTMCapabilities(
    start=True,
    stop=True,
    thickness_reset=True,
    material=True,
    z_ratio=True,
    ftm_scale=True,
    pwm=True,
    pwm_scale=True,
    gate_time=True,
    fault_reset=True,
    target_thickness=False,
)


class TM106B(TM106BProtocolMixin, RS485GatedFTM):
    """TM106B RS485 driver."""

    capabilities = TM106B_CAPABILITIES

    def __init__(
        self,
        con_params: ModbusSerialConnectionConfig,
        address: int = 1,
        label: str = "FTM",
        logger: Logger | None = None,
        chunk_size: int | None = None,
        write_chunk_size: int | None = None,
        **kwargs,
    ):

        con_params.framer = "ASCII"
        super().__init__(
            con_params=con_params,
            address=address,
            label=label,
            logger=logger,
            chunk_size=chunk_size or registers.MAX_READ_REGISTERS,
            write_chunk_size=write_chunk_size,
            **kwargs,
        )

    # RS485 address and baudrate

    async def get_address(self) -> int:
        address = await self.read_register(registers.REG_ADDRESS)
        if isinstance(address, int):
            return address
        self.logger.error("%s: can not read address data.", self.label)
        return 0

    async def set_address(self, address: int) -> int:
        new_address = max(1, min(address, 254))
        await self.write_register(registers.REG_ADDRESS, new_address)
        self.address = new_address
        response = await self.get_address()
        if response is not None and response > 0:
            return response
        return 0

    async def get_baudrate(self) -> int:
        baudrate_code = await self.read_register(registers.REG_BAUDRATE)
        if isinstance(baudrate_code, int):
            return registers.code_to_baudrate(baudrate_code)
        return 0

    async def set_baudrate(self, baudrate: int) -> int:
        if baudrate <= 1200:
            new_baudrate = 1200
        elif baudrate <= 2400:
            new_baudrate = 2400
        elif baudrate <= 4800:
            new_baudrate = 4800
        elif baudrate <= 9600:
            new_baudrate = 9600
        elif baudrate <= 19200:
            new_baudrate = 19200
        else:
            new_baudrate = 38400
        await self.write_register(registers.REG_BAUDRATE, registers.baudrate_to_code(new_baudrate))
        new_con_params = self.con_params
        new_con_params.baudrate = new_baudrate
        self.con_params = new_con_params
        return await self.get_baudrate()

    async def check_connection(self) -> bool:
        vendor = await self.get_vendor()
        if vendor:
            return True
        return False
