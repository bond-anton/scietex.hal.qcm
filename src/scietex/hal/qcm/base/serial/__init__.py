"""Serial communication devices."""

from .gated_ftm import SerialGatedFTM, manage_connection

__all__ = ["SerialGatedFTM", "manage_connection"]
