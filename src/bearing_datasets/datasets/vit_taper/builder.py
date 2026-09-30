"""VIT Vellore taper roller bearings (set 2): ``<H|F1-F4>_<trial>_<rpm>...xlsx`` (Dewesoft
export). Sheet Data1: row 1 channel names (Time, [EXI,] y, x, z, then event columns), row 2
units, then samples at 12.8 kHz (~10 s). Other sheets hold derived spectra and are not used."""

import re

import pandas as pd

CHANNELS = {
    **{
        axis: {
            "sensor_location": "test_bearing_housing",
            "quantity": "acceleration",
            "axis": axis,
            "unit": "g",
            "fs": 12800,
        }
        for axis in "xyz"
    },
    "exi": {
        "sensor_location": "unknown",
        "quantity": "force",
        "axis": "none",
        "unit": "N",
        "fs": 12800,
    },
}
STATE = {  # code -> (condition, fault description from the record)
    "H": ("normal", "healthy"),
    "F1": ("ball", "single roller taper fault"),
    "F2": ("inner", "inner wedge"),
    "F3": ("bearing", "wear damage on circumference"),
    "F4": ("cage", "inner cage fault"),
}
NAME = re.compile(
    r"^(?P<state>H|F[1-4])_(?:Trail|trail|trial)_?(?P<trial>\d)_(?:at_)?(?P<rpm>\d+)_?rpm$"
)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.xlsx")):
        m = NAME.match(path.stem)
        condition, fault = STATE[m["state"]]
        sheet = pd.read_excel(path, sheet_name="Data1", header=None)
        names = [str(n).strip() for n in sheet.iloc[0]]
        data = sheet.iloc[2:]
        signals = {
            ch: pd.to_numeric(data.iloc[:, names.index(src)]).to_numpy()
            for ch, src in [("x", "x"), ("y", "y"), ("z", "z"), ("exi", "EXI")]
            if src in names
        }
        yield {
            "recording_id": f"{m['state']}_trial{m['trial']}_{m['rpm']}rpm",
            "native_label": m["state"],
            "condition": condition,
            "fault_location": "none" if condition == "normal" else "test_bearing",
            "fault_origin": "none" if condition == "normal" else "artificial",
            "fault": fault,
            "rpm": float(m["rpm"]),
            "trial": int(m["trial"]),
            "signals": signals,
        }
