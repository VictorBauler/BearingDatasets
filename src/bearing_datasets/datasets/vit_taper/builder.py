"""VIT Vellore taper roller bearings (set 2): ``<H|F1-F4>_<trial>_<rpm>...xlsx`` (Dewesoft
export). Sheet Data1: row 1 channel names (Time, [EXI,] y, x, z, then event columns), row 2
units, then samples at 12.8 kHz (~10 s). Other sheets hold derived spectra and are not used."""

import re

import pandas as pd

CHANNELS = {
    **{
        axis: {
            "sensor_location": "test_bearing",
            "sensor_mounting": "pedestal",
            "quantity": "acceleration",
            "axis": axis,
            "unit": "g",
            "fs": 12800,
        }
        for axis in "xyz"
    },
    "exi": {
        "sensor_location": "unknown",
        "sensor_mounting": "unknown",
        "quantity": "force",
        "axis": "none",
        "unit": "N",
        "fs": 12800,
    },
}
STATE = {  # code -> (fault_type, fault description from the record)
    "H": ("normal", "healthy"),
    "F1": ("rolling_element", "single roller taper fault"),
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
        fault_type, detail = STATE[m["state"]]
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
            "fault_type": fault_type,
            "fault_location": "none" if fault_type == "normal" else "test_bearing",
            "fault_origin": "none" if fault_type == "normal" else "artificial",
            "fault_detail": detail,
            "speed_rpm": float(m["rpm"]),
            "repetition": int(m["trial"]),
            "signals": signals,
        }
