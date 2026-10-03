"""MCC5-THU gearbox: ``<state>[_<L|M|H>]_<speed|torque>_circulation_<settings>.csv``, e.g.
``teeth_break_and_bearing_inner_H_speed_circulation_20Nm-2000rpm.csv`` (speed cycling up to
2000 rpm at 20 Nm) or ``gear_wear_M_torque_circulation_1000rpm_10Nm.csv`` (load cycling up to
10 Nm at 1000 rpm). 60 s at 12.8 kHz; columns: speed (key phase), torque, motor_vibration_x/y/z,
gearbox_vibration_x/y/z. The zip also holds macOS ``._*`` files, skipped."""

import re

import pandas as pd

from bearing_datasets.bearings import fault_orders


def _ch(location, mounting, quantity, axis="none", unit="g"):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 12800,
    }


# ER-16K: 9 balls of 7.94 mm, pitch diameter 38.52 mm (Huang & Baddour 2018, as ottawa_2018)
ORDERS = fault_orders(9, 7.94, 38.52)
CHANNELS = {
    "speed": _ch("motor_shaft", "shaft", "tachometer", unit="unknown"),
    "torque": _ch("gearbox_shaft_input", "shaft", "torque", unit="Nm"),
    # x axial, y horizontal, z vertical
    "motor_vibration_x": _ch("motor_bearing_de", "casing", "acceleration", "axial"),
    "motor_vibration_y": _ch("motor_bearing_de", "casing", "acceleration", "horizontal"),
    "motor_vibration_z": _ch("motor_bearing_de", "casing", "acceleration", "vertical"),
    "gearbox_vibration_x": _ch("gearbox_bearing_intermediate", "casing", "acceleration", "axial"),
    "gearbox_vibration_y": _ch("gearbox_bearing_intermediate", "casing", "acceleration",
                               "horizontal"),
    "gearbox_vibration_z": _ch("gearbox_bearing_intermediate", "casing", "acceleration",
                               "vertical"),
}  # fmt: skip
BEARING = "gearbox_bearing_intermediate"
STATE = {  # state -> (fault_type, fault_location)
    "health": ("normal", "none"),
    "miss_teeth": ("gear", "gearbox"),
    "gear_pitting": ("gear", "gearbox"),
    "gear_wear": ("gear", "gearbox"),
    "teeth_crack": ("gear", "gearbox"),
    "teeth_break": ("gear", "gearbox"),
    "teeth_break_and_bearing_inner": ("gear+inner", f"gearbox+{BEARING}"),
    "teeth_break_and_bearing_outer": ("gear+outer", f"gearbox+{BEARING}"),
}
# severity -> (words, level); missing teeth is not graded: level 1
SEVERITY = {"L": ("light", 1), "M": ("medium", 2), "H": ("high", 3), None: ("not graded", 1)}
NAME = re.compile(
    r"^(?P<state>[a-z_]+?)(?:_(?P<sev>[LMH]))?_(?P<varying>speed|torque)_circulation_"
    r"(?:(?P<nm1>\d+)Nm-(?P<rpm1>\d+)rpm|(?P<rpm2>\d+)rpm_(?P<nm2>\d+)Nm)$"
)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/**/*.csv")):
        if path.name.startswith("._") or "__MACOSX" in path.parts:
            continue
        m = NAME.match(path.stem)
        fault_type, location = STATE[m["state"]]
        severity, level = SEVERITY[m["sev"]] if fault_type != "normal" else ("none", 0)
        x = pd.read_csv(path, engine="pyarrow", dtype="float64")
        yield {
            "recording_id": path.stem,
            "native_label": m["state"] + (f"_{m['sev']}" if m["sev"] else ""),
            "fault_type": fault_type,
            "fault_location": location,
            "fault_severity": severity,
            "fault_severity_level": level,
            # the speed cycles, or the load cycles at a constant speed
            "speed_profile": "varying" if m["varying"] == "speed" else "constant",
            "speed_rpm": float(m["rpm1"] or m["rpm2"]),
            "load": float(m["nm1"] or m["nm2"]),
            "load_unit": "Nm",
            "bearing_model": "ER-16K",
            **ORDERS,
            "signals": {ch: x[ch].to_numpy() for ch in CHANNELS},
        }
