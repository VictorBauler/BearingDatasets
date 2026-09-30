"""MCC5-THU gearbox: ``<state>[_<L|M|H>]_<speed|torque>_circulation_<settings>.csv``, e.g.
``teeth_break_and_bearing_inner_H_speed_circulation_20Nm-2000rpm.csv`` (speed cycling up to
2000 rpm at 20 Nm) or ``gear_wear_M_torque_circulation_1000rpm_10Nm.csv`` (load cycling up to
10 Nm at 1000 rpm). 60 s at 12.8 kHz; columns: speed (key phase), torque, motor_vibration_x/y/z,
gearbox_vibration_x/y/z. The zip also holds macOS ``._*`` files, skipped."""

import re

import pandas as pd

from bearing_datasets.bearings import fault_orders


def _ch(location, quantity, axis="none", unit="g"):
    return {
        "sensor_location": location,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 12800,
    }


# ER-16K: 9 balls of 7.94 mm, pitch diameter 38.52 mm (Huang & Baddour 2018, as ottawa_2018)
ORDERS = fault_orders(9, 7.94, 38.52)
CHANNELS = {
    "speed": _ch("motor_shaft", "tachometer", unit="dimensionless"),
    "torque": _ch("gearbox_input_shaft", "torque", unit="Nm"),
    "motor_vibration_x": _ch("motor_de", "acceleration", "x"),
    "motor_vibration_y": _ch("motor_de", "acceleration", "y"),
    "motor_vibration_z": _ch("motor_de", "acceleration", "z"),
    "gearbox_vibration_x": _ch("gearbox_intermediate_shaft", "acceleration", "x"),
    "gearbox_vibration_y": _ch("gearbox_intermediate_shaft", "acceleration", "y"),
    "gearbox_vibration_z": _ch("gearbox_intermediate_shaft", "acceleration", "z"),
}
STATE = {  # state -> (condition, fault_location)
    "health": ("normal", "none"),
    "miss_teeth": ("gear", "gearbox"),
    "gear_pitting": ("gear", "gearbox"),
    "gear_wear": ("gear", "gearbox"),
    "teeth_crack": ("gear", "gearbox"),
    "teeth_break": ("gear", "gearbox"),
    "teeth_break_and_bearing_inner": ("gear+inner", "gearbox+intermediate_shaft_bearing"),
    "teeth_break_and_bearing_outer": ("gear+outer", "gearbox+intermediate_shaft_bearing"),
}
SEVERITY = {"L": "light", "M": "medium", "H": "high", None: "none"}
NAME = re.compile(
    r"^(?P<state>[a-z_]+?)(?:_(?P<sev>[LMH]))?_(?P<varying>speed|torque)_circulation_"
    r"(?:(?P<nm1>\d+)Nm-(?P<rpm1>\d+)rpm|(?P<rpm2>\d+)rpm_(?P<nm2>\d+)Nm)$"
)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/**/*.csv")):
        if path.name.startswith("._") or "__MACOSX" in path.parts:
            continue
        m = NAME.match(path.stem)
        condition, location = STATE[m["state"]]
        x = pd.read_csv(path, engine="pyarrow", dtype="float64")
        yield {
            "recording_id": path.stem,
            "native_label": m["state"] + (f"_{m['sev']}" if m["sev"] else ""),
            "condition": condition,
            "fault_location": location,
            "severity": SEVERITY[m["sev"]],
            "varying": "speed" if m["varying"] == "speed" else "load",
            "rpm_setting": float(m["rpm1"] or m["rpm2"]),
            "torque_setting_nm": float(m["nm1"] or m["nm2"]),
            **ORDERS,
            "signals": {ch: x[ch].to_numpy() for ch in CHANNELS},
        }
