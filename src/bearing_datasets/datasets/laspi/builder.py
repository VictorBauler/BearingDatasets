"""LASPI gearbox: ``<state>/<Hz>hz_<load>%_<rpm>rpm/acc_0000<n>.csv`` (n = 1-4 acquisitions of 10 s
at 25.6 kHz), no header, 7 columns: currents 1-3 (reduction gain 100), vibration (100 mV/g),
voltages 1-3 (reduction gain 200). macOS ``._*`` files are skipped."""

import re

import pandas as pd

from bearing_datasets.bearings import fault_orders


def _ch(location, mounting, quantity, axis, sensitivity):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": "V",
        "sensitivity": sensitivity,
        "fs": 25600,
    }


# intermediate-shaft ball bearing from the record: 9 balls of 0.3125 in, pitch 1.5157 in
ORDERS = fault_orders(9, 0.3125, 1.5157)
# currents and voltages at the inverter output (the motor supply)
CHANNELS = {
    "current_1": _ch("motor_supply", "none", "current", "a", "unknown"),
    "current_2": _ch("motor_supply", "none", "current", "b", "unknown"),
    "current_3": _ch("motor_supply", "none", "current", "c", "unknown"),
    "vibration": _ch("gearbox_bearing_intermediate", "casing", "acceleration", "none",
                     "100 mV/g"),
    "voltage_1": _ch("motor_supply", "none", "voltage", "a", "5 mV/V"),
    "voltage_2": _ch("motor_supply", "none", "voltage", "b", "5 mV/V"),
    "voltage_3": _ch("motor_supply", "none", "voltage", "c", "5 mV/V"),
}  # fmt: skip
BEARING = "gearbox_bearing_intermediate"
STATE = {  # folder -> (fault_type, fault_location); the gears are on the intermediate shaft
    "Healthy_motor": ("normal", "none"),
    "Bearing_inner_race_fault": ("inner", BEARING),
    "Bearing_outer_race_fault": ("outer", BEARING),
    "Gear_surface_damage": ("gear", "gearbox"),
    "Gear_half_broken_tooth": ("gear", "gearbox"),
    "Gear_surface_and_bearing_inner_race_faults": ("gear+inner", f"gearbox+{BEARING}"),
    "Gear_half_broken_tooth_and_bearing_outer_race_faults": ("gear+outer", f"gearbox+{BEARING}"),
}
COND = re.compile(r"^(?P<hz>\d+)hz_(?P<load>\d+)%_(?P<rpm>\d+)rpm$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("LASPI*/LASPI*/*/*/acc_*.csv")):
        if path.name.startswith("._"):
            continue
        state, cond = path.parent.parent.name, COND.match(path.parent.name)
        fault_type, location = STATE[state]
        x = pd.read_csv(path, header=None, engine="c")
        yield {
            "recording_id": f"{state}_{path.parent.name.replace('%', 'pct')}_{path.stem[-1]}",
            "native_label": state,
            "fault_type": fault_type,
            "fault_location": location,
            "speed_rpm": float(cond["rpm"]),
            "supply_hz": float(cond["hz"]),
            "load": float(cond["load"]),
            "load_unit": "% of brake",
            "repetition": int(path.stem[-1]),
            **ORDERS,
            "signals": {ch: x.iloc[:, i].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
