"""Tests for the TM106B Modbus/TCP driver against a fake gateway client."""

import asyncio

import pytest

from scietex.hal.qcm.cyky import registers
from scietex.hal.qcm.cyky.tm106b_modbus import TM106BModbus


class FakeResponse:
    """Minimal stand-in for a pymodbus response."""

    def __init__(self, registers: list[int] | None = None):
        self.registers = registers or []


class FakeClient:
    """Records requests and answers from an in-memory register map."""

    def __init__(self, values: dict[int, int] | None = None):
        self.values = dict(values or {})
        self.reads: list[tuple[int, int]] = []
        self.writes: list[tuple[int, int]] = []
        self.connected = False

    async def connect(self) -> bool:
        self.connected = True
        return True

    def close(self) -> None:
        self.connected = False

    async def read_holding_registers(self, address: int, count: int = 1, device_id: int = 1):
        self.reads.append((address, count))
        return FakeResponse([self.values.get(address + i, 0) for i in range(count)])

    async def read_input_registers(self, address: int, count: int = 1, device_id: int = 1):
        return await self.read_holding_registers(address, count=count, device_id=device_id)

    async def write_register(self, address: int, value: int, device_id: int = 1):
        self.writes.append((address, value))
        self.values[address] = value
        return FakeResponse()


@pytest.fixture
def driver() -> TM106BModbus:
    """A driver wired to a fake client preloaded with the live register block."""
    d = TM106BModbus(host="127.0.0.1", port=15020, unit_id=3, label="qcm-1")
    d._client = FakeClient(
        {
            registers.REG_VERSION: 100,
            registers.REG_CON: 41504,
            registers.REG_RUN: 1,
            registers.REG_DENSITY: 720,
            registers.REG_Z_RATIO: 310,
            registers.REG_FTM_SCALE: 1000,
        }
    )
    return d


def test_connect_and_close():
    """connect opens the client and close drops it."""
    d = TM106BModbus(host="127.0.0.1", port=15020, unit_id=3)
    d._client = FakeClient()
    asyncio.run(d.connect())
    assert d._client is not None and d._client.connected is True
    asyncio.run(d.close())
    assert d._client is None


def test_read_requires_connection():
    """Reading before connect raises instead of silently returning None."""
    from scietex.hal.serial import ModbusOperationError

    d = TM106BModbus(host="127.0.0.1", port=15020, unit_id=3)
    with pytest.raises(ModbusOperationError):
        asyncio.run(d.read_register(0))


def test_reads_are_chunked_to_five_registers(driver: TM106BModbus):
    """A twelve-register read is split into chunks the device can answer."""
    asyncio.run(driver.read_parameters())
    client = driver._client
    assert client is not None
    assert all(count <= registers.MAX_READ_REGISTERS for _, count in client.reads)
    assert sum(count for _, count in client.reads) == registers.PARAMETERS_COUNT
    assert client.reads[0][0] == registers.PARAMETERS_START


def test_chunk_boundaries(driver: TM106BModbus):
    """Chunks cover the requested range without gaps or overlap."""
    asyncio.run(driver.read_registers(0, count=12))
    client = driver._client
    assert client is not None
    covered = []
    for start, count in client.reads:
        covered.extend(range(start, start + count))
    assert covered == list(range(0, 12))


def test_read_parameters_decodes(driver: TM106BModbus):
    """The chunked block decodes to the live device values."""
    params = asyncio.run(driver.read_parameters())
    assert params.material_density == pytest.approx(7.20)
    assert params.material_z_ratio == pytest.approx(0.310)
    assert params.scale == pytest.approx(1.000)
    assert params.running is True


def test_set_ftm_scale_writes_register_12(driver: TM106BModbus):
    """set_ftm_scale writes the FTM scale register and leaves Z-ratio alone."""
    asyncio.run(driver.set_ftm_scale(1.5))
    client = driver._client
    assert client is not None
    assert client.writes[-1] == (registers.REG_FTM_SCALE, 1500)
    assert asyncio.run(driver.get_material_z_ratio()) == pytest.approx(0.310)


def test_check_connection(driver: TM106BModbus):
    """check_connection probes the firmware register."""
    assert asyncio.run(driver.check_connection()) is True


def test_capabilities():
    """The Modbus driver advertises the TM106B capability set."""
    caps = TM106BModbus.capabilities
    assert caps.start and caps.stop and caps.thickness_reset
    assert caps.material and caps.z_ratio and caps.ftm_scale
    assert caps.pwm and caps.pwm_scale and caps.gate_time
    assert caps.target_thickness is False
