"""Tests for the TM106B register protocol against a fake transport."""

import asyncio

import pytest
from scietex.hal.serial import ModbusSerialConnectionConfig

from scietex.hal.qcm.base.data import Material, PwmCTRLMode
from scietex.hal.qcm.cyky import TM106B, registers
from scietex.hal.qcm.cyky.protocol import TM106BProtocolMixin


class FakeTransport(TM106BProtocolMixin):
    """In-memory transport recording every register access."""

    def __init__(self, values: dict[int, int] | None = None):
        import logging

        self.logger = logging.getLogger("fake")
        self.label = "fake"
        self.registers = dict(values or {})
        self.reads: list[tuple[int, int]] = []
        self.writes: list[tuple[int, int]] = []

    async def read_registers(
        self, start_register: int = 0, count: int = 1, holding: bool = True
    ) -> list[int] | None:
        self.reads.append((start_register, count))
        return [self.registers.get(start_register + i, 0) for i in range(count)]

    async def read_register(self, register: int, holding: bool = True) -> int | None:
        values = await self.read_registers(register, count=1, holding=holding)
        return values[0] if values else None

    async def write_register(self, register: int, value: int) -> None:
        self.writes.append((register, value))
        self.registers[register] = value

    async def read_register_float(
        self, register: int, factor: int = 100, holding: bool = True
    ) -> float | None:
        value = await self.read_register(register, holding=holding)
        return None if value is None else value / factor

    async def write_register_float(self, register: int, value: float, factor: int = 100) -> None:
        await self.write_register(register, int(round(value * factor)))

    async def read_two_registers_float(
        self,
        start_register: int,
        factor: int | float = 100,
        holding: bool = True,
        byteorder=None,
    ) -> float | None:
        from scietex.hal.serial.utilities.numeric import ByteOrder, combine_32bit

        values = await self.read_registers(start_register, count=2, holding=holding)
        if not values or len(values) < 2:
            return None
        return (
            combine_32bit(values[0], values[1], byteorder=byteorder or ByteOrder.BIG_ENDIAN)
            / factor
        )


class FakeTM106B(FakeTransport):
    """Fake transport bound to the real TM106B baudrate helpers.

    The helpers are pulled off ``TM106B`` directly: inheriting the class would
    drag in the RS485 client, whose label setter needs a live transport.
    """

    get_baudrate = TM106B.get_baudrate
    set_baudrate = TM106B.set_baudrate

    def __init__(self, values: dict[int, int] | None = None):
        FakeTransport.__init__(self, values)
        self.con_params = ModbusSerialConnectionConfig(port="fake", baudrate=19200)


@pytest.fixture
def transport() -> FakeTransport:
    """A transport preloaded with the live device register block."""
    return FakeTransport(
        {
            registers.REG_VERSION: 100,
            registers.REG_PWM_VALUE: 2,
            registers.REG_CON: 41504,
            registers.REG_RUN: 1,
            registers.REG_DENSITY: 720,
            registers.REG_Z_RATIO: 310,
            registers.REG_FTM_SCALE: 1000,
            registers.REG_PWM_SCALE: 5000,
            registers.REG_ADDRESS: 3,
            registers.REG_BAUDRATE: 0x4000,  # 19200 (code 4 << 12)
        }
    )


def test_get_version(transport: FakeTransport):
    """The firmware register is scaled by 100."""
    assert asyncio.run(transport.get_version()) == "1.00"


def test_get_con(transport: FakeTransport):
    """The CON word decodes to gate 10, manual PWM, 10-average."""
    assert asyncio.run(transport.get_con()) == (10, 2, 2)


def test_set_con_writes_encoded_word(transport: FakeTransport):
    """set_con writes the packed word, not a formatted string."""
    asyncio.run(transport.set_con(5, 1, 0))
    assert transport.writes[-1] == (registers.REG_CON, registers.encode_con(5, 1, 0))
    assert asyncio.run(transport.get_con()) == (5, 1, 0)


def test_set_con_clamps_gate_time(transport: FakeTransport):
    """Gate time is clamped to the hardware range 1..10."""
    asyncio.run(transport.set_con(0, 1, 1))
    assert asyncio.run(transport.get_con())[0] == registers.GATE_TIME_MIN
    asyncio.run(transport.set_con(99, 1, 1))
    assert asyncio.run(transport.get_con())[0] == registers.GATE_TIME_MAX


def test_set_gate_time_preserves_other_fields(transport: FakeTransport):
    """Changing the gate time leaves PWM mode and rate mode untouched."""
    asyncio.run(transport.set_gate_time(500))
    assert asyncio.run(transport.get_con()) == (5, 2, 2)


def test_set_ftm_scale_writes_register_12(transport: FakeTransport):
    """set_ftm_scale must write the FTM scale register, never the Z-ratio."""
    asyncio.run(transport.set_ftm_scale(1.5))
    assert transport.writes[-1] == (registers.REG_FTM_SCALE, 1500)
    assert registers.REG_Z_RATIO not in [r for r, _ in transport.writes]
    assert asyncio.run(transport.get_material_z_ratio()) == pytest.approx(0.310)


def test_set_material(transport: FakeTransport):
    """Setting a material writes density and Z-ratio."""
    result = asyncio.run(transport.set_material(Material(density=2.65, z_ratio=1.0)))
    assert result.density == pytest.approx(2.65)
    assert result.z_ratio == pytest.approx(1.0)


def test_set_material_clamps(transport: FakeTransport):
    """Density and Z-ratio are clamped to the hardware ranges."""
    result = asyncio.run(transport.set_material(Material(density=0.1, z_ratio=99.0)))
    assert result.density == pytest.approx(0.4)
    assert result.z_ratio == pytest.approx(9.999)


def test_pwm_mode_round_trip(transport: FakeTransport):
    """PWM mode maps to the analog-output nibble."""
    assert asyncio.run(transport.get_ctrl_pwm_mode()) == PwmCTRLMode.MANUAL
    asyncio.run(transport.set_ctrl_pwm_mode(PwmCTRLMode.ABSOLUTE))
    assert asyncio.run(transport.get_ctrl_pwm_mode()) == PwmCTRLMode.ABSOLUTE
    asyncio.run(transport.set_ctrl_pwm_mode(PwmCTRLMode.DISABLED))
    assert asyncio.run(transport.get_ctrl_pwm_mode()) == PwmCTRLMode.DISABLED


def test_set_ctrl_pwm_value(transport: FakeTransport):
    """PWM value is scaled by 100."""
    asyncio.run(transport.set_ctrl_pwm_value(12.34))
    assert transport.writes[-1] == (registers.REG_PWM_VALUE, 1234)


def test_set_ctrl_pwm_scale_clamps(transport: FakeTransport):
    """PWM scale is clamped to 1..9999."""
    assert asyncio.run(transport.set_ctrl_pwm_scale(0)) == 1
    assert asyncio.run(transport.set_ctrl_pwm_scale(99999)) == 9999


def test_run_round_trip(transport: FakeTransport):
    """Running state round-trips through the RUN word."""
    assert asyncio.run(transport.get_running_state()) is True
    asyncio.run(transport.set_running_state(False))
    assert asyncio.run(transport.get_running_state()) is False
    asyncio.run(transport.start_measurement(reset=False))
    assert asyncio.run(transport.get_running_state()) is True


def test_reset_thickness_preserves_running_state(transport: FakeTransport):
    """A thickness reset keeps the current running state."""
    asyncio.run(transport.reset_thickness())
    assert transport.writes[-1] == (registers.REG_RUN, registers.encode_run(1, 1))


def test_read_parameters_uses_one_block(transport: FakeTransport):
    """read_parameters issues a single block read of the parameter registers."""
    params = asyncio.run(transport.read_parameters())
    assert transport.reads == [(registers.PARAMETERS_START, registers.PARAMETERS_COUNT)]
    assert params.material_density == pytest.approx(7.20)
    assert params.material_z_ratio == pytest.approx(0.310)
    assert params.scale == pytest.approx(1.000)
    assert params.running is True


def test_target_thickness_unsupported(transport: FakeTransport):
    """The TM106B has no target thickness register."""
    assert asyncio.run(transport.get_target_thickness()) == 0.0
    assert asyncio.run(transport.set_target_thickness(1000.0)) == 0.0


def test_get_baudrate_decodes_high_nibble():
    """Register 15 decodes the rate code from bits 12-15."""
    ftm = FakeTM106B({registers.REG_BAUDRATE: 0x4000})
    assert asyncio.run(ftm.get_baudrate()) == 19200


def test_set_baudrate_writes_shifted_word_and_keeps_con_params():
    """A baudrate write stores the shifted code without switching the link."""
    ftm = FakeTM106B({registers.REG_BAUDRATE: 0x4000})
    assert asyncio.run(ftm.set_baudrate(9600)) == 9600
    assert ftm.writes[-1] == (registers.REG_BAUDRATE, 0x3000)
    assert ftm.con_params.baudrate == 19200
