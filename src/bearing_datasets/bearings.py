"""Bearing fault characteristic frequencies from the bearing geometry."""

from __future__ import annotations

import math


def fault_orders(balls: int, ball_d: float, pitch_d: float, contact_deg: float = 0.0) -> dict:
    """``bpfo``, ``bpfi``, ``bsf``, ``ftf`` in orders of the shaft speed (multiples of the
    rotation frequency; Hz = order x rpm / 60), for a rotating inner ring.

    ``bsf`` is the ball spin frequency (ball defects mostly show at 2 x bsf, as they hit both
    races on each turn). Diameters in any unit, the same for both.
    """
    r = ball_d / pitch_d * math.cos(math.radians(contact_deg))
    return {
        "bpfo": round(balls / 2 * (1 - r), 5),
        "bpfi": round(balls / 2 * (1 + r), 5),
        "bsf": round(pitch_d / (2 * ball_d) * (1 - r * r), 5),
        "ftf": round((1 - r) / 2, 5),
    }
