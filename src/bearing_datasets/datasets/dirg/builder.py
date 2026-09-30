"""Politecnico di Torino DIRG: ``VariableSpeedAndLoad/C<n>A_<speed Hz>_<load cell mV>_<m>.mat``
(51.2 kHz, 10 s) and ``EnduranceTest/E4A[_]<nnn>.mat`` (102.4 kHz, 8 s). Each file holds one
matrix named like the file, 6 columns: x (axial), y, z (radial) of accelerometer A1 (support
of the tested bearing B1), then of A2 (support of the loaded bearing B2), in m/s^2."""

import re

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

CHANNELS = {
    f"{point}_{axis}": {
        "sensor_location": location,
        "quantity": "acceleration",
        "axis": axis,
        "unit": "m/s^2",
        "fs": 51200,
    }
    for point, location in [("A1", "bearing_b1_support"), ("A2", "bearing_b2_support")]
    for axis in "xyz"
}
# dataset description, Table 1: B1 (and B3) 10 rollers of 9.0 mm on 40.5 mm; B2 16 of 8.0 on 54.0
ORDERS_B1, ORDERS_B2 = fault_orders(10, 9.0, 40.5), fault_orders(16, 8.0, 54.0)
ORDERS = {k: {ch: (ORDERS_B1 if ch.startswith("A1") else ORDERS_B2)[k] for ch in CHANNELS}
          for k in ORDERS_B1}  # fmt: skip
DEFECT = {  # code -> (condition, indentation diameter in mm)
    "0": ("normal", 0.0),
    "1": ("inner", 0.45),
    "2": ("inner", 0.25),
    "3": ("inner", 0.15),
    "4": ("ball", 0.45),  # roller
    "5": ("ball", 0.25),
    "6": ("ball", 0.15),
}
STATIONARY = re.compile(r"^C(?P<n>[0-6])A_(?P<hz>\d{3})_(?P<mv>\d{3})_(?P<m>[12])$")
ENDURANCE = re.compile(r"^E4A_?(?P<nnn>\d{3})$")


def _row(name, code, rpm, load, session, acquisition):
    condition, size = DEFECT[code]
    return {
        "recording_id": name,
        "native_label": f"{code}A",
        "condition": condition,
        "fault_location": "none" if code == "0" else "bearing_b1",
        "fault_origin": "none" if code == "0" else "artificial",
        "fault_size_mm": size,
        "rpm": rpm,
        "load": load,
        "load_unit": "N",
        "session": session,
        "acquisition": acquisition,
    }


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("VariableSpeedAndLoad/**/C*.mat")):
        m = STATIONARY.match(path.stem)
        (x,) = read_mat(path).values()
        load = round(int(m["mv"]) / 0.499)  # load cell sensitivity 0.499 mV/N
        yield {
            **_row(path.stem, m["n"], int(m["hz"]) * 60.0, float(load), "stationary", m["m"]),
            **ORDERS,
            "signals": {ch: x[:, i] for i, ch in enumerate(CHANNELS)},
        }
    for path in sorted(raw_dir.glob("EnduranceTest/**/E4A*.mat")):
        m = ENDURANCE.match(path.stem)
        (x,) = read_mat(path).values()
        yield {
            **_row(path.stem, "4", 18000.0, 1800.0, "endurance", m["nnn"]),
            "fs": 102400,
            **ORDERS,
            "signals": {ch: x[:, i] for i, ch in enumerate(CHANNELS)},
        }
