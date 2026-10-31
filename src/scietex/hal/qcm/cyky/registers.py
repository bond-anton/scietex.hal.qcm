"""
CYKY TM106B register map and word codecs.

The TM106B exposes sixteen holding registers. Multi-byte measurements are
32-bit big-endian pairs; the CON and RUN words pack three and two nibbles
respectively. Every codec here is a pure function so the serial and Modbus/TCP
drivers share one definition of the wire format.

The device answers reads of at most :data:`MAX_READ_REGISTERS` registers; a
longer request times out on the bus. Callers must chunk larger reads.

Functions:
    parse_con: Split the CON word into gate time, analog output and rate mode.
    encode_con: Build the CON word from its three fields.
    parse_run: Split the RUN word into running state and thickness reset.
    encode_run: Build the RUN word from its two fields.
    parse_averaging: Map the rate-mode code to an averaging window size.
    code_to_baudrate: Map the baudrate register code to bits per second.
    baudrate_to_code: Map bits per second to the baudrate register code.
    decode_parameters: Build FTMParameters from a register block.
"""

from scietex.hal.serial.utilities.numeric import ByteOrder, combine_32bit

from ..base.data import FTMParameters

REG_VERSION = 0
REG_THICKNESS = 1
REG_RATE = 3
REG_FREQUENCY = 5
REG_PWM_VALUE = 7
REG_CON = 8
REG_RUN = 9
REG_DENSITY = 10
REG_Z_RATIO = 11
REG_FTM_SCALE = 12
REG_PWM_SCALE = 13
REG_ADDRESS = 14
REG_BAUDRATE = 15

#: The device answers at most five registers per read; six or more times out.
MAX_READ_REGISTERS = 5

#: First register and length of the block read by :func:`decode_parameters`.
PARAMETERS_START = REG_THICKNESS
PARAMETERS_COUNT = 12

#: Gate time is stored in units of 100 ms and the hardware accepts 1..10.
GATE_TIME_UNIT_MS = 100
GATE_TIME_MIN = 1
GATE_TIME_MAX = 10

BAUDRATE_CODES: dict[int, int] = {
    0: 1200,
    1: 2400,
    2: 4800,
    3: 9600,
    4: 19200,
    5: 38400,
}


def parse_con(con: int) -> tuple[int, int, int]:
    """
    Split the CON word into its three fields.

    The word is laid out as ``a b c 0``: ``a`` is the gate time in units of
    100 ms, ``b`` the analog output mode (0 stop, 1 auto, 2 manual) and ``c``
    the rate algorithm (0 immediate, 1 weighted, 2 ten-sample average).
    """
    return (con >> 12) & 0xF, (con >> 8) & 0xF, (con >> 4) & 0xF


def encode_con(a: int, b: int, c: int) -> int:
    """Build the CON word from its three fields; inverse of :func:`parse_con`."""
    return ((a & 0xF) << 12) | ((b & 0xF) << 8) | ((c & 0xF) << 4)


def parse_run(run: int) -> tuple[int, int]:
    """
    Split the RUN word into running state and thickness reset.

    The word is laid out as ``0 0 y x``: ``x`` is the running state (0 stopped,
    1 started) and ``y`` requests a thickness reset (0 no, 1 yes).
    """
    return run & 0xF, (run >> 4) & 0xF


def encode_run(x: int, y: int) -> int:
    """Build the RUN word from running state and thickness reset."""
    return ((y & 0xF) << 4) | (x & 0xF)


def parse_averaging(c: int) -> int:
    """Map the rate-mode code to the number of samples averaged."""
    if c in (0, 1):
        return 1
    if c == 2:
        return 10
    return 0


def code_to_baudrate(code: int) -> int:
    """Map the baudrate register code to bits per second; 0 when unknown."""
    return BAUDRATE_CODES.get(code, 0)


def baudrate_to_code(baudrate: int) -> int:
    """Map bits per second to the baudrate register code; 9600 when unknown."""
    for code, value in BAUDRATE_CODES.items():
        if value == baudrate:
            return code
    return 3


def decode_parameters(registers: list[int]) -> FTMParameters:
    """
    Build FTMParameters from the twelve-register block starting at REG_THICKNESS.

    Args:
        registers: Twelve consecutive register values, thickness first.

    Returns:
        FTMParameters: The decoded snapshot, marked connected.

    Raises:
        ValueError: If fewer than twelve registers are supplied.
    """
    if len(registers) < PARAMETERS_COUNT:
        raise ValueError(f"Expected {PARAMETERS_COUNT} registers, got {len(registers)}")
    thickness = combine_32bit(registers[0], registers[1], byteorder=ByteOrder.BIG_ENDIAN) / 100.0
    rate = combine_32bit(registers[2], registers[3], byteorder=ByteOrder.BIG_ENDIAN) / 100.0
    frequency = combine_32bit(registers[4], registers[5], byteorder=ByteOrder.BIG_ENDIAN) / 100.0
    _, _, c = parse_con(registers[7])
    averaging_window = parse_averaging(c)
    x, _ = parse_run(registers[8])
    return FTMParameters(
        connected=True,
        frequency=frequency,
        frequency_std=0.0,
        averaging_window=averaging_window,
        averaging_progress=averaging_window,
        rate=rate,
        thickness=thickness,
        thickness_std=0.0,
        target=0.0,
        material_density=registers[9] / 100.0,
        material_z_ratio=registers[10] / 1000.0,
        running=bool(x),
        scale=registers[11] / 1000.0,
    )
