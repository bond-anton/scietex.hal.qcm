"""
CYKY TM106B FTM behind the Scietex Modbus gateway.

The gateway owns the RS485 bus and speaks Modbus ASCII to the TM106B; this
client speaks plain Modbus/TCP (FC03/FC06) and addresses the device by its
Modbus unit id. It never touches the RS485 framing.

The device answers at most five registers per read, so every read is chunked
at :data:`scietex.hal.qcm.cyky.registers.MAX_READ_REGISTERS`.

Classes:
    TM106BModbus: A Modbus/TCP client for the CYKY TM106B.
"""

from logging import Logger, getLogger

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.pdu import ExceptionResponse
from scietex.hal.serial import ModbusOperationError
from scietex.hal.serial.utilities.numeric import ByteOrder, combine_32bit, float_to_int

from ..base.data import GatedFTMCapabilities, OutCTRLMode
from ..base.gated_ftm import GatedFTM
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


class TM106BModbus(TM106BProtocolMixin, GatedFTM):
    """TM106B driver addressing the device through the Modbus gateway."""

    capabilities = TM106B_CAPABILITIES
    display_name = "CYKY TM106B"

    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 1,
        label: str = "TM106B",
        timeout: float = 1.0,
        logger: Logger | None = None,
        chunk_size: int | None = None,
    ):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.label = label
        self.timeout = timeout
        self.chunk_size = chunk_size or registers.MAX_READ_REGISTERS
        self.logger = logger or getLogger(__name__)
        self._client: AsyncModbusTcpClient | None = None

    # Transport

    async def connect(self) -> None:
        """Open the TCP connection to the gateway."""
        if self._client is None:
            self._client = AsyncModbusTcpClient(
                host=self.host, port=self.port, timeout=self.timeout
            )
        if not await self._client.connect():
            raise ModbusOperationError(
                f"{self.label}: could not connect to gateway {self.host}:{self.port}"
            )

    async def close(self) -> None:
        """Close the TCP connection to the gateway."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _require_client(self) -> AsyncModbusTcpClient:
        if self._client is None:
            raise ModbusOperationError(f"{self.label}: transport is not connected")
        return self._client

    # Register primitives

    async def read_registers(
        self,
        start_register: int = 0,
        count: int = 1,
        holding: bool = True,
    ) -> list[int] | None:
        """Read registers, chunked to the device's per-request limit."""
        client = self._require_client()
        values: list[int] = []
        current = start_register
        remaining = count
        while remaining > 0:
            chunk = min(self.chunk_size, remaining)
            if holding:
                response = await client.read_holding_registers(
                    current, count=chunk, device_id=self.unit_id
                )
            else:
                response = await client.read_input_registers(
                    current, count=chunk, device_id=self.unit_id
                )
            if isinstance(response, ExceptionResponse):
                raise ModbusOperationError(
                    f"{self.label}: read of registers {current}-{current + chunk - 1} "
                    f"failed: exception code {response.exception_code}"
                )
            values.extend(response.registers)
            current += chunk
            remaining -= chunk
        return values

    async def read_register(self, register: int, holding: bool = True) -> int | None:
        """Read a single register."""
        values = await self.read_registers(register, count=1, holding=holding)
        if not values:
            return None
        return values[0]

    async def write_register(self, register: int, value: int) -> None:
        """Write a single register."""
        client = self._require_client()
        response = await client.write_register(register, value, device_id=self.unit_id)
        if isinstance(response, ExceptionResponse):
            raise ModbusOperationError(
                f"{self.label}: write of register {register} failed: "
                f"exception code {response.exception_code}"
            )

    async def read_register_float(
        self,
        register: int,
        factor: int = 100,
        holding: bool = True,
    ) -> float | None:
        """Read a single register and divide it by ``factor``."""
        value = await self.read_register(register, holding=holding)
        if value is None:
            return None
        return value / factor

    async def write_register_float(
        self,
        register: int,
        value: float,
        factor: int = 100,
    ) -> None:
        """Multiply ``value`` by ``factor`` and write it to a register."""
        await self.write_register(register, float_to_int(value, factor))

    async def read_two_registers_float(
        self,
        start_register: int,
        factor: int | float = 100,
        holding: bool = True,
        byteorder: ByteOrder = ByteOrder.LITTLE_ENDIAN,
    ) -> float | None:
        """Read a 32-bit value from two registers and divide it by ``factor``."""
        values = await self.read_registers(start_register, count=2, holding=holding)
        if not values or len(values) < 2:
            return None
        return combine_32bit(values[0], values[1], byteorder=byteorder) / factor

    # Error handling

    async def get_error_code(self, comm: bool = False) -> int:
        """The TM106B reports no error codes over Modbus."""
        return 0

    async def clear_error(self, comm: bool = False) -> int:
        """The TM106B has no error register to clear."""
        return await self.get_error_code(comm)

    async def get_serial_number(self) -> str:
        """The TM106B does not expose a serial number over Modbus."""
        return "n/d"

    async def get_mcu_frequency(self) -> int:
        """The TM106B does not expose the MCU frequency over Modbus."""
        return 0

    async def get_averaging_progress(self) -> int:
        """The TM106B reports no separate averaging progress."""
        return await self.get_averaging()

    async def get_frequency(self) -> float:
        """Get frequency."""
        return await self.get_frequency_instant()

    async def get_frequency_std(self) -> float:
        """The TM106B reports no frequency standard deviation."""
        return 0.0

    async def get_thickness_std(self) -> float:
        """The TM106B reports no thickness standard deviation."""
        return 0.0

    async def get_ctrl_out_mode(self) -> OutCTRLMode:
        """The TM106B has no discrete control output."""
        return OutCTRLMode.DISABLED

    async def set_ctrl_out_mode(self, mode: OutCTRLMode) -> OutCTRLMode:
        """The TM106B has no discrete control output."""
        return await self.get_ctrl_out_mode()

    async def get_ctrl_out_value(self) -> bool:
        """The TM106B has no discrete control output."""
        return False

    async def set_ctrl_out_value(self, value: bool) -> bool:
        """The TM106B has no discrete control output."""
        return await self.get_ctrl_out_value()

    async def check_connection(self) -> bool:
        """Probe the device by reading its firmware version register."""
        try:
            version = await self.read_register(registers.REG_VERSION)
        except ModbusOperationError:
            return False
        return version is not None
