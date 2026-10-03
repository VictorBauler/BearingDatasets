"""KAIST varying load: ``<load>Nm_<state>[_<severity>]`` in three folders, each a separate
acquisition: ``vibration/*.mat`` and ``acoustic/*.mat`` (Simcenter Test.Lab ``Signal``
structs) and ``current,temp/*.tdms`` (NI FlexLogger). Some vibration files are misspelled
``Unbalalnce``."""

import re

from nptdms import TdmsFile

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat


def _ch(location, mounting, quantity, axis="none", unit="unknown", fs=25600):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": fs,
    }


# NSK 6205 DDU in housing A (Jung et al. 2023, Table 1): 9 balls of 7.90 mm, pitch 38.5 mm;
# the paper's BSF is 2 x BSF
ORDERS = fault_orders(9, 7.90, 38.5)
# housing A holds the test bearing, housing B a support bearing
CHANNELS = {
    "x_housing_a": _ch("test_bearing", "pedestal", "acceleration", "x", "m/s^2"),
    "y_housing_a": _ch("test_bearing", "pedestal", "acceleration", "y", "m/s^2"),
    "x_housing_b": _ch("support_bearing", "pedestal", "acceleration", "x", "m/s^2"),
    "y_housing_b": _ch("support_bearing", "pedestal", "acceleration", "y", "m/s^2"),
    "temperature_housing_a": _ch("test_bearing", "pedestal", "temperature", unit="degC",
                                 fs=25608),
    "temperature_housing_b": _ch("support_bearing", "pedestal", "temperature", unit="degC",
                                 fs=25608),
    "current_u": _ch("motor_supply", "none", "current", "a", "A", 25608),
    "current_v": _ch("motor_supply", "none", "current", "b", "A", 25608),
    "current_w": _ch("motor_supply", "none", "current", "c", "A", 25608),
    "microphone": _ch("ambient", "none", "sound_pressure", unit="Pa", fs=51200),
}  # fmt: skip
TDMS = {  # FlexLogger channel -> ours, in the order of the record's description
    "cDAQ9185-1F486B5Mod1/ai0": "temperature_housing_a",
    "cDAQ9185-1F486B5Mod1/ai1": "temperature_housing_b",
    "cDAQ9185-1F486B5Mod2/ai0": "current_u",
    "cDAQ9185-1F486B5Mod2/ai2": "current_v",
    "cDAQ9185-1F486B5Mod2/ai3": "current_w",
}
STATE = {  # state -> (fault_type, fault_location, severity unit)
    "Normal": ("normal", "none", ""),
    "BPFI": ("inner", "test_bearing", "mm"),
    "BPFO": ("outer", "test_bearing", "mm"),
    "Misalign": ("misalignment", "rig_shaft", "mm"),
    "Unbalance": ("unbalance", "rig_rotor", "mg"),
}
NAME = re.compile(r"^(?P<load>\d)Nm_(?P<state>[A-Za-z]+?)(?:_(?P<sev>\d+)(?:mg)?)?$")


def _levels(raw_dir):
    """Severity level of each (state, severity code): 1, 2, ... from the smallest."""
    codes = {}
    for path in raw_dir.glob("*/**/*.*"):
        if (m := NAME.match(path.stem.replace("Unbalalnce", "Unbalance"))) and m["sev"]:
            codes.setdefault(m["state"], set()).add(int(m["sev"]))
    return {(s, c): i + 1 for s, cs in codes.items() for i, c in enumerate(sorted(cs))}


def _label(stem, levels):
    m = NAME.match(stem.replace("Unbalalnce", "Unbalance"))
    fault_type, location, unit = STATE[m["state"]]
    if unit == "mm":
        severity = f"{int(m['sev']) / 10:.1f} mm"  # 03 -> 0.3 mm
    elif unit == "mg":
        severity = f"{int(m['sev'])} mg"
    else:
        severity = "none"
    return {
        "native_label": stem.replace("Unbalalnce", "Unbalance"),
        "fault_type": fault_type,
        "fault_location": location,
        "fault_severity": severity,
        "fault_severity_level": levels[(m["state"], int(m["sev"]))] if m["sev"] else 0,
        "bearing_model": "6205 DDU",
        "speed_rpm": 3010.0,
        "load": float(m["load"]),
        "load_unit": "Nm",
    }


def _signal(path):
    s = read_mat(path)["Signal"][0, 0]
    return s["y_values"]["values"][0, 0]


def recordings(raw_dir):
    levels = _levels(raw_dir)
    for path in sorted(raw_dir.glob("vibration/**/*.mat")):
        x = _signal(path)
        yield {
            "recording_id": f"{path.stem.replace('Unbalalnce', 'Unbalance')}_vibration",
            **_label(path.stem, levels),
            **ORDERS,
            "signals": {ch: x[:, i] for i, ch in enumerate(list(CHANNELS)[:4])},
        }
    for path in sorted(raw_dir.glob("current,temp/**/*.tdms")):
        log = TdmsFile.read(path)["Log"]
        yield {
            "recording_id": f"{path.stem}_current_temperature",
            **_label(path.stem, levels),
            # phases V and W are empty in the outer race files
            **ORDERS,
            "signals": {TDMS[c.name]: c[:] for c in log.channels() if len(c)},
        }
    for path in sorted(raw_dir.glob("acoustic/**/*.mat")):
        yield {
            "recording_id": f"{path.stem}_acoustic",
            **_label(path.stem, levels),
            **ORDERS,
            "signals": {"microphone": _signal(path)[:, 0]},
        }
