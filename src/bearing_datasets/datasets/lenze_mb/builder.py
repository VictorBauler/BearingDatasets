"""Lenze-MB: ``Data/H1.<n>.mat``, one (16, 524288) matrix ``StromBox_Werte`` sampled by the
inverter at 16 kHz. Rows: sampling time, then the 11 channels below; rows 12-15 are unused
(zero). Labels and operating conditions come from ``Meta_Data.xlsx``, copied to meta.csv."""

from pathlib import Path

import pandas as pd

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat


def _ch(name, quantity, axis, unit, location="motor_supply", mounting="none"):
    return name, {  # logged by the inverter: the motor supply, or its encoder on the shaft
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 16000,
    }


# FAG NU2205-E-XL-TVP2 (dataset report): 13 rollers; running diameters 31.5 / 46.5 mm give
# rollers of 7.5 mm on a 39 mm pitch
ORDERS = fault_orders(13, 7.5, 39)
CHANNELS = dict(
    [
        _ch("current_u", "current", "a", "A"),
        _ch("current_v", "current", "b", "A"),
        _ch("current_w", "current", "c", "A"),
        _ch("voltage_u", "voltage", "a", "V"),
        _ch("voltage_v", "voltage", "b", "V"),
        _ch("voltage_w", "voltage", "c", "V"),
        _ch("dc_bus_voltage", "voltage", "none", "V"),
        _ch(
            "angle",
            "angle",
            "none",
            "counts",
            "motor_shaft",
            "shaft",
        ),
        _ch("current_vector", "current", "none", "counts"),
        _ch("speed", "speed", "none", "counts", "motor_shaft", "shaft"),
        _ch("speed_deviation", "speed", "none", "counts", "motor_shaft", "shaft"),
    ]
)
META = Path(__file__).with_name("meta.csv")
LEVEL = {"normal": 0, "pitting_I": 1, "pitting_II": 2, "pitting_III": 3, "pitting_IV": 4,
         "pitting_V": 5, "scientific_fault": 6}  # fmt: skip


def recordings(raw_dir):
    meta = pd.read_csv(META).set_index("id")
    for path in sorted(raw_dir.glob("Data/**/H1.*.mat"), key=lambda p: int(p.stem.split(".")[1])):
        m = meta.loc[path.stem]
        x = read_mat(path)["StromBox_Werte"]
        yield {
            "recording_id": path.stem,
            "native_label": m["condition"],
            "fault_type": "normal" if m["condition"] == "normal" else "inner",
            "fault_location": "none" if m["condition"] == "normal" else "test_bearing",
            "fault_severity": "none" if m["condition"] == "normal" else m["condition"],
            "fault_severity_level": LEVEL[m["condition"]],
            "bearing_model": "NU2205-E-XL-TVP2",
            "speed_rpm": float(m["rpm"]),
            "load": float(m["counter_torque_nm"]),
            "load_unit": "Nm",
            "belt_tension": float(m["belt_tension"]),
            **ORDERS,
            "signals": {ch: x[i + 1] for i, ch in enumerate(CHANNELS)},
        }
