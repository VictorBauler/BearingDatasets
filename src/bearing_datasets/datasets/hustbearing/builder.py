"""HUSTbearing: ``[0.5X_]<H|I|O|B|C>_<speed>.xls``, e.g. ``0.5X_B_65Hz.xls`` (medium ball
fault at 65 Hz) or ``C_VS_0_40_0Hz.xls``. The .xls files are SpectraQuest text exports:
a 21-line header, then tab-separated time, speed (meaningless), X, Y, Z."""

import re

import pandas as pd

from bearing_datasets.bearings import fault_orders

# ER-16K: 9 balls of 7.94 mm, pitch diameter 38.52 mm (Huang & Baddour 2018, as ottawa_2018)
ORDERS = fault_orders(9, 7.94, 38.52)
CHANNELS = {
    axis: {
        "sensor_location": "test_bearing",
        "sensor_mounting": "unknown",
        "quantity": "acceleration",
        "axis": axis.lower(),
        "unit": "V",
        "sensitivity": "100 mV/g",  # TREA331, nominal (+-15 %)
        "fs": 25600,
    }
    for axis in "XYZ"
}
FAULT_TYPE = {"H": "normal", "I": "inner", "O": "outer", "B": "rolling_element", "C": "inner+outer"}
SIZE_MM = {"I": 0.3, "O": 0.3, "B": 0.5, "C": 0.3}  # severe; medium (0.5X) is half
NAME = re.compile(r"^(?P<medium>0\.5X_)?(?P<code>[HIOBC])_(?P<speed>\d+Hz|VS_0_40_0Hz)$", re.I)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.xls")):
        m = NAME.match(path.stem)
        code, healthy = m["code"], m["code"] == "H"
        speed = m["speed"].replace("hz", "Hz")  # one file is named H_25hz
        fault_type = FAULT_TYPE[code]
        severity = "none" if healthy else "medium" if m["medium"] else "severe"
        x = pd.read_csv(path, sep="\t", skiprows=22, header=None, usecols=[2, 3, 4])
        yield {
            "recording_id": path.stem,
            "native_label": path.stem,
            "fault_type": fault_type,
            "fault_location": "none"
            if healthy
            else "+".join(["test_bearing"] * len(fault_type.split("+"))),
            "fault_origin": "none" if healthy else "artificial",
            "fault_size_mm": 0.0 if healthy else SIZE_MM[code] / (2 if m["medium"] else 1),
            "fault_severity": severity,
            "fault_severity_level": {"none": 0, "medium": 1, "severe": 2}[severity],
            "bearing_model": "ER-16K",
            "bearing_id": "healthy" if healthy else f"{severity}_{code}",
            "operating_condition": "0-40-0Hz" if speed.startswith("VS") else speed,
            "speed_profile": "inc_dec" if speed.startswith("VS") else "constant",
            **ORDERS,
            "signals": {axis: x[i + 2].to_numpy() for i, axis in enumerate("XYZ")},
        }
