"""Signal units: the ``unit`` vocabulary and conversion between units of one dimension.

A signal keeps the values of the raw files. ``unit`` says what they are in: a physical unit
(``g``, ``m/s^2``, ``A``, ...), the volts of an uncalibrated sensor (``V``, with the sensor
``sensitivity`` when the dataset documents it, e.g. ``"100 mV/g"``), or raw values that cannot be
converted (``counts`` from an ADC, ``normalized`` audio in [-1, 1], ``unknown``).
"""

from __future__ import annotations

import numpy as np

# unit -> (dimension, factor to the SI unit of that dimension); factor None: not convertible
UNITS = {
    # acceleration
    "m/s^2": ("acceleration", 1.0),
    "mm/s^2": ("acceleration", 1e-3),
    "g": ("acceleration", 9.80665),
    # velocity
    "m/s": ("velocity", 1.0),
    "mm/s": ("velocity", 1e-3),
    "um/s": ("velocity", 1e-6),
    "in/s": ("velocity", 0.0254),
    # displacement
    "m": ("displacement", 1.0),
    "mm": ("displacement", 1e-3),
    "um": ("displacement", 1e-6),
    "mil": ("displacement", 2.54e-5),
    # electrical
    "V": ("voltage", 1.0),
    "mV": ("voltage", 1e-3),
    "A": ("current", 1.0),
    "mA": ("current", 1e-3),
    # mechanical
    "N": ("force", 1.0),
    "kN": ("force", 1e3),
    "Nm": ("torque", 1.0),
    "Pa": ("sound_pressure", 1.0),
    "dB": ("sound_pressure", None),  # a level, not proportional to the pressure
    "rpm": ("speed", 1 / 60),
    "Hz": ("speed", 1.0),  # shaft speed in revolutions per second
    "rad": ("angle", 1 / (2 * np.pi)),
    "deg": ("angle", 1 / 360),
    "rev": ("angle", 1.0),
    "degC": ("temperature", None),
    "s": ("time", 1.0),
    "ms": ("time", 1e-3),
    # raw values
    "counts": ("raw", None),  # integer samples of an ADC (or of a 16-bit audio file)
    "normalized": ("raw", None),  # audio samples scaled to [-1, 1]
    "unknown": ("raw", None),
}

# units any quantity may be stored in: the sensor's volts, or raw values
RAW_UNITS = {"V", "mV", "counts", "normalized", "unknown"}


def allowed_units(quantity: str) -> set[str]:
    """Units a signal of this ``quantity`` may be stored in."""
    if quantity == "unknown":
        return set(UNITS)
    return RAW_UNITS | {u for u, (dim, _) in UNITS.items() if dim == quantity}


def parse_sensitivity(text: str) -> tuple[float, str, str] | None:
    """``"100 mV/g"`` -> ``(100.0, "mV", "g")``; None for ``none`` / ``unknown``."""
    if text in ("none", "unknown"):
        return None
    try:
        value, ratio = text.split(" ", 1)
        num, den = ratio.split("/", 1)
        den = den.removeprefix("(").removesuffix(")")
        out = float(value), num, den
    except ValueError:
        out = None
    if out is None or num not in UNITS or den not in UNITS or UNITS[den][1] is None:
        raise ValueError(
            f"sensitivity {text!r}: write '<value> <stored unit>/<physical unit>', "
            "e.g. '100 mV/g' or '10.2 mV/(m/s^2)'"
        )
    return out


def convert(
    x: np.ndarray, unit: str, to: str, sensitivity: str = "none", dtype=np.float64
) -> np.ndarray:
    """Samples ``x`` stored in ``unit`` converted to ``to``.

    Signals stored in volts with a ``sensitivity`` (``"100 mV/g"``) are first divided by it,
    whatever ``to`` is (a voltage divider of ``"5 mV/V"`` gives the measured voltage in V).
    Raises ``ValueError`` when the conversion is not a change of unit (unknown or raw units,
    acceleration to velocity, ...).
    """
    if to not in UNITS:
        raise ValueError(f"unknown unit {to!r}; units: {', '.join(UNITS)}")
    if unit not in UNITS:
        raise ValueError(f"cannot convert from {unit!r}: not a unit of {', '.join(UNITS)}")
    scale = 1.0
    dim, factor = UNITS[unit]
    if sens := parse_sensitivity(sensitivity):  # volts of a sensor: to its physical unit first
        value, num, den = sens
        if dim != "voltage" or UNITS[num][0] != "voltage":
            raise ValueError(f"sensitivity {sensitivity!r} of a signal in {unit!r}: not volts")
        scale = factor / (value * UNITS[num][1])
        unit, (dim, factor) = den, UNITS[den]
    if unit == to:
        return np.asarray(x * scale if sens else x, dtype=dtype)
    to_dim, to_factor = UNITS[to]
    if factor is None or to_factor is None:
        why = {
            "unknown": "the dataset does not document the unit",
            "counts": "raw ADC values, no calibration documented",
            "normalized": "audio scaled to [-1, 1], no calibration documented",
        }.get(unit, "not a linear unit")
        raise ValueError(f"cannot convert {unit!r} to {to!r}: {why}")
    if dim != to_dim:
        hint = " (no sensor sensitivity documented)" if dim == "voltage" else ""
        raise ValueError(f"cannot convert {unit!r} ({dim}) to {to!r} ({to_dim}){hint}")
    return np.asarray(x * (scale * factor / to_factor), dtype=dtype)
