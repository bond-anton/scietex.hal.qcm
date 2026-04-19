"""Data models for the QCM."""

from enum import Enum

import msgspec


class OutCTRLMode(Enum):
    """Modes of the control output."""

    HIGH = 1
    LOW = 2
    MANUAL = 3
    DISABLED = 4


class PwmCTRLMode(Enum):
    """Modes of the PWM output."""

    ABSOLUTE = 1
    RELATIVE = 2
    MANUAL = 3
    DISABLED = 4


class QCMError(msgspec.Struct, frozen=True):
    """Model of a QCM error with code and message."""

    code: int
    message: str = "Unknown error"

    def __str__(self) -> str:
        return f"QCMError(code={self.code}, message='{self.message}')"


class FTMParameters(msgspec.Struct, frozen=True):
    """Model for FTM operational parameters."""

    connected: bool = False  # FTM connection status
    frequency: float | None = None  # Sensor frequency
    frequency_std: float | None = None  # Sensor frequency standard deviation
    averaging_window: int | None = None  # Averaging window size
    averaging_progress: int | None = None  # Averaging accumulation progress
    rate: float | None = None  # Deposition rate A/s
    thickness: float | None = None  # Film thickness A
    thickness_std: float | None = None  # Film thickness standard deviation A
    target: float | None = None  # Film target thickness A
    material_density: float | None = None  # Material density g/cm^3
    material_z_ratio: float | None = None  # Material Z-ratio
    running: bool = False  # Current FTM measurement running state
    scale: float | None = None  # Scale (tooling) factor

    def __str__(self) -> str:
        f_str = f"{self.frequency:g} Hz" if self.frequency is not None else "N/A"
        f_std_str = f"{self.frequency_std:g} Hz" if self.frequency_std is not None else "N/A"
        a_prog_str = f"{self.averaging_progress}" if self.averaging_progress is not None else "N/A"
        a_win_str = f"{self.averaging_window}" if self.averaging_window is not None else "N/A"
        rate_str = f"{self.rate:g} A/s" if self.rate is not None else "N/A"
        thickness_str = f"{self.thickness:g} A" if self.thickness is not None else "N/A"
        thickness_std_str = f"{self.thickness_std:g} A" if self.thickness_std is not None else "N/A"
        target_str = f"{self.target:g} A" if self.target is not None else "N/A"
        density_str = (
            f"{self.material_density:g} g/cm^3" if self.material_density is not None else "N/A"
        )
        z_ratio_str = f"{self.material_z_ratio:g}" if self.material_z_ratio is not None else "N/A"
        scale_str = f"{self.scale:g}" if self.scale is not None else "N/A"

        return (
            f"FTMParameters(frequency={f_str} +- {f_std_str} Hz, "
            f"averaging={a_prog_str}/{a_win_str}, "
            f"deposition rate={rate_str}, "
            f"film thickness={thickness_str} +- {thickness_std_str} A, "
            f"target thickness={target_str} A, "
            f"material density={density_str}, "
            f"material Z-ratio={z_ratio_str}, "
            f"scale={scale_str}, "
            f"running={self.running}, "
            f"connected={self.connected})"
        )


class FTMStartCMD(msgspec.Struct, frozen=True):
    """FTM start command with parameters."""

    reset: bool = True  # Reset thickness at start

    def __str__(self) -> str:
        return f"FTMStartCMD(reset={self.reset})"


class Material(msgspec.Struct, frozen=True):
    """Material parameters."""

    density: float  # Density g/cm^3
    z_ratio: float  # Z-ratio

    def __str__(self) -> str:
        return f"Material(density={self.density}, Z-ratio={self.z_ratio})"
