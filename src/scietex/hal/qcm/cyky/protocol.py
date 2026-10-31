"""
CYKY TM106B register protocol.

The TM106B speaks the same register map over RS485 and through the Scietex
Modbus gateway, so every register operation lives here and the two transports
only supply the register primitives. A transport must provide
``read_registers``, ``read_register``, ``write_register``,
``read_register_float``, ``write_register_float`` and
``read_two_registers_float``, plus ``logger`` and ``label``.

Classes:
    TM106BProtocolMixin: Register-level TM106B operations.
"""

from logging import Logger
from typing import Protocol, cast

from scietex.hal.serial.utilities.numeric import ByteOrder

from ..base.data import FTMParameters, Material, PwmCTRLMode
from . import registers


class TM106BTransport(Protocol):
    """Register primitives a TM106B transport must provide."""

    logger: Logger
    label: str

    async def read_registers(
        self, start_register: int = 0, count: int = 1, holding: bool = True
    ) -> list[int] | None: ...

    async def read_register(self, register: int, holding: bool = True) -> int | None: ...

    async def write_register(self, register: int, value: int) -> None: ...

    async def read_register_float(
        self, register: int, factor: int = 100, holding: bool = True
    ) -> float | None: ...

    async def write_register_float(
        self, register: int, value: float, factor: int = 100
    ) -> None: ...

    async def read_two_registers_float(
        self,
        start_register: int,
        factor: int | float = 100,
        holding: bool = True,
        byteorder: ByteOrder = ByteOrder.LITTLE_ENDIAN,
    ) -> float | None: ...


class TM106BProtocolMixin:
    """Register-level TM106B operations shared by every transport."""

    logger: Logger
    label: str

    def _transport(self) -> TM106BTransport:
        """View ``self`` through the transport protocol for type checking."""
        return cast(TM106BTransport, self)

    # Device information

    async def get_vendor(self) -> str:
        return "CYKY"

    async def get_product_name(self) -> str:
        return "TM106B"

    async def get_version(self) -> str:
        version = await self._transport().read_register_float(registers.REG_VERSION, factor=100)
        if version is None:
            self.logger.error("%s: can not read register", self.label)
            return ""
        return f"{version:.2f}"

    # CON parameters

    async def get_con(self) -> tuple[int, int, int]:
        """
        Get and parse CON parameters from register data.
        a: 1-10 gate time = a * 100ms
        b: Analog output (b=0 stop, b=1 auto, b=2 manual)
        c: rate calculation algorithm (c=0 immediate, c=1 weighted, c=2 10-average)
        """
        response = await self._transport().read_register(registers.REG_CON)
        if response is not None:
            a, b, c = registers.parse_con(response)
            self.logger.debug(
                "%s: t: %d ms, PWM mode: %d, Rate mode: %d", self.label, a * 100, b, c
            )
            return a, b, c
        self.logger.error("%s: can not read register.", self.label)
        return 0, 0, 0

    async def set_con(self, a: int = 1, b: int = 1, c: int = 1) -> None:
        """
        Set CON values to register.
        a: 1-10 gate time = a * 100ms
        b: Analog output (b=0 stop, b=1 auto, b=2 manual)
        c: rate calculation algorithm (c=0 immediate, c=1 weighted, c=2 10-average)
        """
        a = int(round(max(registers.GATE_TIME_MIN, min(a, registers.GATE_TIME_MAX))))
        b = int(round(max(0, min(b, 2))))
        c = int(round(max(0, min(c, 2))))
        await self._transport().write_register(registers.REG_CON, registers.encode_con(a, b, c))

    async def get_gate_time(self) -> float:
        a, _, _ = await self.get_con()
        return float(registers.GATE_TIME_UNIT_MS * a)

    async def set_gate_time(self, gate_time_ms: float) -> float:
        _, b, c = await self.get_con()
        a_new = int(round(gate_time_ms / registers.GATE_TIME_UNIT_MS))
        await self.set_con(a_new, b, c)
        return await self.get_gate_time()

    async def get_averaging(self) -> int:
        _, _, c = await self.get_con()
        return registers.parse_averaging(c)

    async def set_averaging(self, averaging_window: int) -> int:
        a, b, _ = await self.get_con()
        c = 1
        if averaging_window == 0:
            c = 0
        elif averaging_window >= 10:
            c = 2
        await self.set_con(a, b, c)
        return await self.get_averaging()

    # Frequency and thickness

    async def get_frequency_instant(self) -> float:
        frequency = await self._transport().read_two_registers_float(
            registers.REG_FREQUENCY, factor=100, byteorder=ByteOrder.BIG_ENDIAN
        )
        if isinstance(frequency, float):
            return frequency
        self.logger.error("%s: can not read frequency data.", self.label)
        return 0.0

    async def get_counter(self) -> int:
        frequency = await self.get_frequency_instant()
        gate_time = await self.get_gate_time() / 1000  # in convert to seconds
        return int(round(frequency * gate_time))

    async def get_thickness(self) -> float:
        thickness = await self._transport().read_two_registers_float(
            registers.REG_THICKNESS, factor=100, byteorder=ByteOrder.BIG_ENDIAN
        )
        if isinstance(thickness, float):
            return thickness
        self.logger.error("%s: can not read thickness data.", self.label)
        return 0.0

    async def get_rate(self) -> float:
        rate = await self._transport().read_two_registers_float(
            registers.REG_RATE, factor=100, byteorder=ByteOrder.BIG_ENDIAN
        )
        if isinstance(rate, float):
            return rate
        self.logger.error("%s: can not read rate data.", self.label)
        return 0.0

    # Material

    async def get_material_density(self) -> float:
        density = await self._transport().read_register_float(registers.REG_DENSITY, factor=100)
        if isinstance(density, float):
            return density
        self.logger.error("%s: can not read density data.", self.label)
        return 0.0

    async def set_material_density(self, density: float) -> float:
        await self._transport().write_register_float(
            registers.REG_DENSITY, max(0.4, min(density, 99.99)), factor=100
        )
        return await self.get_material_density()

    async def get_material_z_ratio(self) -> float:
        z_ratio = await self._transport().read_register_float(registers.REG_Z_RATIO, factor=1000)
        if isinstance(z_ratio, float):
            return z_ratio
        self.logger.error("%s: can not read Z-ratio data.", self.label)
        return 0.0

    async def set_material_z_ratio(self, z_ratio: float) -> float:
        await self._transport().write_register_float(
            registers.REG_Z_RATIO, max(0.1, min(z_ratio, 9.999)), factor=1000
        )
        return await self.get_material_z_ratio()

    async def get_material(self) -> Material:
        density = await self.get_material_density()
        z_ratio = await self.get_material_z_ratio()
        return Material(density=density, z_ratio=z_ratio)

    async def set_material(self, material: Material) -> Material:
        await self.set_material_density(material.density)
        await self.set_material_z_ratio(material.z_ratio)
        return await self.get_material()

    async def get_ftm_scale(self) -> float:
        scale = await self._transport().read_register_float(registers.REG_FTM_SCALE, factor=1000)
        if isinstance(scale, float):
            return scale
        self.logger.error("%s: can not read scale data.", self.label)
        return 0.0

    async def set_ftm_scale(self, scale: float) -> float:
        await self._transport().write_register_float(
            registers.REG_FTM_SCALE, max(0.001, min(scale, 65.535)), factor=1000
        )
        return await self.get_ftm_scale()

    async def get_target_thickness(self) -> float:
        return 0.0

    async def set_target_thickness(self, target: float) -> float:
        return await self.get_target_thickness()

    # PWM parameters

    async def get_ctrl_pwm_mode(self) -> PwmCTRLMode:
        _, b, _ = await self.get_con()
        if b == 0:
            return PwmCTRLMode.DISABLED
        if b == 1:
            return PwmCTRLMode.ABSOLUTE
        if b == 2:
            return PwmCTRLMode.MANUAL
        return PwmCTRLMode.DISABLED

    async def set_ctrl_pwm_mode(self, mode: PwmCTRLMode) -> PwmCTRLMode:
        a, _, c = await self.get_con()
        b = 0
        if mode == PwmCTRLMode.MANUAL:
            b = 2
        elif mode == PwmCTRLMode.ABSOLUTE:
            b = 1
        await self.set_con(a, b, c)
        return await self.get_ctrl_pwm_mode()

    async def get_ctrl_pwm_value(self) -> float:
        pwm = await self._transport().read_register_float(registers.REG_PWM_VALUE, factor=100)
        if isinstance(pwm, float):
            return pwm
        self.logger.error("%s: Can not get pwm value.", self.label)
        return 0.0

    async def set_ctrl_pwm_value(self, value: float) -> float:
        await self._transport().write_register_float(
            registers.REG_PWM_VALUE, max(0.0, min(value, 99.99)), factor=100
        )
        return await self.get_ctrl_pwm_value()

    async def get_ctrl_pwm_scale(self) -> int:
        scale = await self._transport().read_register(registers.REG_PWM_SCALE)
        if isinstance(scale, int):
            return scale
        self.logger.error("%s: Can not get pwm scale value.", self.label)
        return 0

    async def set_ctrl_pwm_scale(self, scale: int) -> int:
        await self._transport().write_register(registers.REG_PWM_SCALE, max(1, min(scale, 9999)))
        return await self.get_ctrl_pwm_scale()

    # RUN parameters

    async def get_run(self) -> tuple[int, int]:
        """
        Get and parse measurement run status.
        (x, y) X: running status, Y: film thickness measurement reset.
        x=0 stopped, x=1 started; y=0 no thickness reset, y=1 thickness reset.
        """
        response = await self._transport().read_register(registers.REG_RUN)
        if response is not None:
            x, y = registers.parse_run(response)
            self.logger.debug("X: %d, Y: %d", x, y)
            return x, y
        return 0, 0

    async def set_run(self, x: int = 0, y: int = 0) -> None:
        """
        Set running status.
        (x, y) X: running status, Y: film thickness measurement reset.
        x=0 stop, x=1 start; y=0 no reset, y=1 reset.
        """
        x = max(0, min(x, 1))
        y = max(0, min(y, 1))
        await self._transport().write_register(registers.REG_RUN, registers.encode_run(x, y))

    async def reset_thickness(self) -> None:
        running, _ = await self.get_run()
        await self.set_run(running, 1)

    async def get_running_state(self) -> bool:
        running, _ = await self.get_run()
        return bool(running)

    async def set_running_state(self, running: bool) -> bool:
        await self.set_run(int(bool(running)), 0)
        return await self.get_running_state()

    async def start_measurement(self, reset: bool = True) -> bool:
        await self.set_run(1, int(bool(reset)))
        return await self.get_running_state()

    # Read FTM state in a single request

    async def read_parameters(self) -> FTMParameters:
        reg_data = await self._transport().read_registers(
            registers.PARAMETERS_START, count=registers.PARAMETERS_COUNT
        )
        if reg_data is None:
            return FTMParameters()
        return registers.decode_parameters(reg_data)
