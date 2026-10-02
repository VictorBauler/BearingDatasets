"""MCC5-THU motor: ``MCC5-THU Motor_<speed|torque>_circulation/<state>_<speed|torque>_circulation_
<N>Nm_<rpm>rpm[_<timestamp>[d]].csv``, no header, 9 columns at 12.8 kHz (90 s): time, key phase,
torque, vibration at the motor drive end (horizontal, axial, vertical), currents A, B, C, all
in V. States can be compound: ``<fault>_and_<fault>``. macOS ``._*`` files are skipped."""

import re

import pandas as pd

from bearing_datasets.bearings import fault_orders


def _ch(location, mounting, quantity, axis="none"):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": "V",
        "fs": 12800,
    }


# SKF 6205-2Z-C3 (data paper, Table 3; Table 7 gives the same BPFO/BPFI/BSF): 9 x 7.94 mm, 39.04
ORDERS = fault_orders(9, 7.94, 39.04)
CHANNELS = {
    "key_phase": _ch("motor_shaft", "shaft", "tachometer"),
    "torque": _ch("gearbox_shaft_input", "shaft", "torque"),
    "vibration_horizontal": _ch("motor_bearing_de", "casing", "acceleration", "horizontal"),
    "vibration_axial": _ch("motor_bearing_de", "casing", "acceleration", "axial"),
    "vibration_vertical": _ch("motor_bearing_de", "casing", "acceleration", "vertical"),
    "current_a": _ch("motor_supply", "none", "current", "a"),
    "current_b": _ch("motor_supply", "none", "current", "b"),
    "current_c": _ch("motor_supply", "none", "current", "c"),
}
FAULT = {  # fault -> (fault_type, fault_location); the faulty bearing's end is not stated
    "bearing_inner": ("inner", "motor_bearing"),
    "bearing_outer": ("outer", "motor_bearing"),
    "bearing_ball": ("rolling_element", "motor_bearing"),
    "bend": ("shaft", "motor_shaft"),
    "broken_bar": ("electrical", "motor_rotor"),
    "dynamic_eccentricity": ("other", "motor_rotor"),
    "static_eccentricity": ("other", "motor_rotor"),
    "voltage_unbalance": ("electrical", "motor_supply"),
    "winding": ("electrical", "motor_stator"),
}
# severity -> (words, level); faults that are not graded get level 1
SEVERITY = {"L": ("light", 1), "H": ("high", 2), None: ("not graded", 1)}
PART = re.compile(r"^(?P<fault>[a-z_]+?)(?:_(?P<sev>[LH]))?$")
NAME = re.compile(
    r"^(?P<state>.+?)_(?P<varying>speed|torque)_circulation_(?P<nm>\d+)Nm_(?P<rpm>\d+)rpm"
    r"(?:_(?P<stamp>\d{12})d?)?$"
)


def _label(state):
    if state == "health":
        return "normal", "none", "none", 0
    # "bearing_outer_H_and_inner_H": the second part drops the "bearing_" prefix
    parts = [
        PART.match(p if not p.startswith(("inner", "outer", "ball")) else f"bearing_{p}")
        for p in state.split("_and_")
    ]
    labels = [FAULT[p["fault"]] for p in parts]
    return (
        "+".join(c for c, _ in labels),
        "+".join(loc for _, loc in labels),
        "+".join(SEVERITY[p["sev"]][0] for p in parts),
        max(SEVERITY[p["sev"]][1] for p in parts),  # the most severe fault
    )


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*/*/*.csv")):
        if path.name.startswith("._"):
            continue
        m = NAME.match(path.stem)
        fault_type, location, severity, level = _label(m["state"])
        x = pd.read_csv(path, header=None, usecols=range(1, 9), engine="c")
        yield {
            "recording_id": path.stem.removesuffix("d"),
            "native_label": m["state"],
            "fault_type": fault_type,
            "fault_location": location,
            "fault_severity": severity,
            "fault_severity_level": level,
            # the speed cycles, or the load cycles at a constant speed
            "speed_profile": "varying" if m["varying"] == "speed" else "constant",
            "speed_setpoint_rpm": float(m["rpm"]),
            "load": float(m["nm"]),
            "load_unit": "Nm",
            "bearing_model": "6205-2Z-C3",
            **ORDERS,
            "signals": {ch: x.iloc[:, i].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
