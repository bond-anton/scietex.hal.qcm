"""Tests for the CYKY TM106B register codecs."""

import pytest

from scietex.hal.qcm.cyky import registers


@pytest.mark.parametrize(
    ("a", "b", "c"),
    [(1, 0, 0), (10, 2, 2), (5, 1, 1), (10, 0, 2)],
)
def test_con_round_trip(a: int, b: int, c: int):
    """encode_con must be the inverse of parse_con."""
    assert registers.parse_con(registers.encode_con(a, b, c)) == (a, b, c)


def test_parse_con_live_word():
    """The live CON word 41504 (0xA220) decodes to gate 10, manual PWM, 10-average."""
    assert registers.parse_con(41504) == (10, 2, 2)


@pytest.mark.parametrize(("x", "y"), [(0, 0), (1, 0), (0, 1), (1, 1)])
def test_run_round_trip(x: int, y: int):
    """encode_run must be the inverse of parse_run."""
    assert registers.parse_run(registers.encode_run(x, y)) == (x, y)


def test_parse_run_live_word():
    """The live RUN word 1 decodes to running with no thickness reset."""
    assert registers.parse_run(1) == (1, 0)


@pytest.mark.parametrize(
    ("code", "window"),
    [(0, 1), (1, 1), (2, 10), (3, 0)],
)
def test_parse_averaging(code: int, window: int):
    """Rate-mode codes map to the documented averaging windows."""
    assert registers.parse_averaging(code) == window


@pytest.mark.parametrize(
    ("baudrate", "code"),
    [
        (1200, 0x0000),
        (2400, 0x1000),
        (4800, 0x2000),
        (9600, 0x3000),
        (19200, 0x4000),
        (38400, 0x5000),
    ],
)
def test_baudrate_round_trip(baudrate: int, code: int):
    """The rate code occupies bits 12-15 of register 15."""
    assert registers.encode_baudrate(baudrate) == code
    assert registers.parse_baudrate(code) == baudrate


def test_baudrate_ignores_low_bits_and_rejects_unknown_rates():
    """Bits 0-11 are ignored on decode; unknown rates are rejected on encode."""
    assert registers.parse_baudrate(0x4ABC) == 19200
    assert registers.parse_baudrate(0x4001) == 19200
    assert registers.parse_baudrate(0x6000) == 0
    with pytest.raises(ValueError):
        registers.encode_baudrate(12345)


def test_decode_parameters_live_block():
    """The live register block decodes to the values read from the device."""
    block = [
        0,  # thickness high
        0,  # thickness low
        0,  # rate high
        0,  # rate low
        0,  # frequency high
        0,  # frequency low
        2,  # PWM value
        41504,  # CON
        1,  # RUN
        720,  # density
        310,  # Z-ratio
        1000,  # FTM scale
    ]
    params = registers.decode_parameters(block)
    assert params.connected is True
    assert params.material_density == pytest.approx(7.20)
    assert params.material_z_ratio == pytest.approx(0.310)
    assert params.scale == pytest.approx(1.000)
    assert params.averaging_window == 10
    assert params.running is True


def test_decode_parameters_32bit_values():
    """32-bit measurements combine big-endian and scale by 100."""
    block = [0x0000, 0x0102, 0x0000, 0x0064, 0x0001, 0x0000, 0, 0, 0, 0, 0, 0]
    params = registers.decode_parameters(block)
    assert params.thickness == pytest.approx(258 / 100)
    assert params.rate == pytest.approx(1.00)
    assert params.frequency == pytest.approx(655.36)


def test_decode_parameters_rejects_short_block():
    """A block shorter than twelve registers is rejected."""
    with pytest.raises(ValueError):
        registers.decode_parameters([0] * 11)
