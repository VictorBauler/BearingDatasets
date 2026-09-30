"""LASPI gearbox: ``<state>/<Hz>hz_<load>%_<rpm>rpm/acc_0000<n>.csv`` (n = 1-4 acquisitions of 10 s
at 25.6 kHz), no header, 7 columns: currents 1-3 (reduction gain 100), vibration (100 mV/g),
voltages 1-3 (reduction gain 200). macOS ``._*`` files are skipped."""

import re

import pandas as pd

from bearing_datasets.bearings import fault_orders


def _ch(location, quantity, axis, unit):
    return {
        "sensor_location": location,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 25600,
    }


# intermediate-shaft ball bearing from the record: 9 balls of 0.3125 in, pitch 1.5157 in
ORDERS = fault_orders(9, 0.3125, 1.5157)
CHANNELS = {
    "current_1": _ch("inverter_output", "current", "a", "raw (current / 100)"),
    "current_2": _ch("inverter_output", "current", "b", "raw (current / 100)"),
    "current_3": _ch("inverter_output", "current", "c", "raw (current / 100)"),
    "vibration": _ch("gearbox_intermediate_shaft", "acceleration", "none", "raw (100 mV/g)"),
    "voltage_1": _ch("inverter_output", "voltage", "a", "raw (voltage / 200)"),
    "voltage_2": _ch("inverter_output", "voltage", "b", "raw (voltage / 200)"),
    "voltage_3": _ch("inverter_output", "voltage", "c", "raw (voltage / 200)"),
}
STATE = {  # folder -> (condition, fault_location)
    "Healthy_motor": ("normal", "none"),
    "Bearing_inner_race_fault": ("inner", "intermediate_shaft_bearing"),
    "Bearing_outer_race_fault": ("outer", "intermediate_shaft_bearing"),
    "Gear_surface_damage": ("gear", "gearbox"),
    "Gear_half_broken_tooth": ("gear", "gearbox"),
    "Gear_surface_and_bearing_inner_race_faults": (
        "gear+inner",
        "gearbox+intermediate_shaft_bearing",
    ),
    "Gear_half_broken_tooth_and_bearing_outer_race_faults": (
        "gear+outer",
        "gearbox+intermediate_shaft_bearing",
    ),
}
COND = re.compile(r"^(?P<hz>\d+)hz_(?P<load>\d+)%_(?P<rpm>\d+)rpm$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("LASPI*/LASPI*/*/*/acc_*.csv")):
        if path.name.startswith("._"):
            continue
        state, cond = path.parent.parent.name, COND.match(path.parent.name)
        condition, location = STATE[state]
        x = pd.read_csv(path, header=None, engine="c")
        yield {
            "recording_id": f"{state}_{path.parent.name.replace('%', 'pct')}_{path.stem[-1]}",
            "native_label": state,
            "condition": condition,
            "fault_location": location,
            "rpm": float(cond["rpm"]),
            "supply_hz": float(cond["hz"]),
            "load": float(cond["load"]),
            "load_unit": "% of brake",
            "acquisition": int(path.stem[-1]),
            **ORDERS,
            "signals": {ch: x.iloc[:, i].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
