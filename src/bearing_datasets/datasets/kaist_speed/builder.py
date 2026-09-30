"""KAIST varying speed: three records (``part1``-``part3``) holding
``vibration_<state>_<n>.csv`` (bearingA_x, bearingA_y, bearingB_x, bearingB_y; 25.6 kHz),
``current_<state>_<n>.csv`` (current_R, _S, _T; 100 kHz) and ``rpm_<state>_<n>.csv``
(time, rpm; irregularly sampled), n = 0-6, 300 s each, plus
``vibration_<state>_constant.csv`` (600 s at 3010 rpm, no header row). Vibration, current
and speed come from different acquisition systems: separate recordings."""

import re

import pandas as pd

from bearing_datasets.bearings import fault_orders


def _ch(location, quantity, axis="none", unit="unknown", fs=25600):
    return {"sensor_location": location, "quantity": quantity, "axis": axis, "unit": unit, "fs": fs}


# NSK 6205 (Jung et al. 2023, Table 1): 9 balls of 7.90 mm, pitch diameter 38.5 mm
ORDERS = fault_orders(9, 7.90, 38.5)
CHANNELS = {
    "x_housing_a": _ch("housing_a", "acceleration", "x"),
    "y_housing_a": _ch("housing_a", "acceleration", "y"),
    "x_housing_b": _ch("housing_b", "acceleration", "x"),
    "y_housing_b": _ch("housing_b", "acceleration", "y"),
    "current_r": _ch("motor", "current", "a", "A", 100000),
    "current_s": _ch("motor", "current", "b", "A", 100000),
    "current_t": _ch("motor", "current", "c", "A", 100000),
    # irregularly sampled: fs is the mean rate, the exact times are in speed_time_s
    "speed": _ch("shaft", "speed", unit="rpm", fs=9),
    "speed_time_s": _ch("shaft", "time", unit="s", fs=9),
}
CONDITION = {"normal": "normal", "inner": "inner", "outer": "outer", "ball": "ball"}
NAME = re.compile(r"^(?P<kind>vibration|current|rpm)_(?P<state>[a-z]+)_(?P<n>\d|constant)$")


def _read(path):
    first = path.open(encoding="utf-8").readline()
    header = 0 if first[:1].isalpha() else None  # the *_constant files have no header row
    return pd.read_csv(path, header=header, engine="pyarrow", dtype="float64").to_numpy()


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("part*/**/*.csv")):
        m = NAME.match(path.stem)
        state, n, kind = m["state"], m["n"], m["kind"]
        constant = n == "constant"
        if state == "normal":
            location = "none"
        elif constant:  # the paper only says where the ball fault bearing was
            location = "housing_a" if state == "ball" else "unknown"
        else:
            location = "housing_b"
        x = _read(path)
        if kind == "vibration":
            signals = {ch: x[:, i] for i, ch in enumerate(list(CHANNELS)[:4])}
        elif kind == "current":
            signals = {ch: x[:, i] for i, ch in enumerate(list(CHANNELS)[4:7])}
        else:
            fs = len(x) / (x[-1, 0] - x[0, 0])
            signals = {"speed": x[:, 1], "speed_time_s": x[:, 0]}
        yield {
            "recording_id": path.stem,
            "native_label": state,
            "condition": CONDITION[state],
            "fault_location": location,
            "trial": n,
            "speed_profile": "constant" if constant else "varying",
            **({"fs": {"speed": fs, "speed_time_s": fs}} if kind == "rpm" else {}),
            **ORDERS,
            "signals": signals,
        }
