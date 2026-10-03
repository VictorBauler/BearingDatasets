"""SEU: ``<subset>/<condition>_<speed>_<load>.csv``, 16 header lines then 8 columns,
tab-separated (``bearingset/ball_20_0.csv`` uses commas), with a trailing delimiter."""

import io
import re

import pandas as pd


def _ch(location, mounting, quantity, axis="none"):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": "V",  # every file header: Volts/Unit 1
        "fs": 5120,
    }


CHANNELS = {
    "motor_vibration": _ch("motor", "casing", "acceleration"),
    # two gearboxes, planetary and parallel (the channel name tells which)
    "planetary_x": _ch("gearbox", "casing", "acceleration", "x"),
    "planetary_y": _ch("gearbox", "casing", "acceleration", "y"),
    "planetary_z": _ch("gearbox", "casing", "acceleration", "z"),
    "motor_torque": _ch("motor_shaft", "shaft", "torque"),
    "parallel_x": _ch("gearbox", "casing", "acceleration", "x"),
    "parallel_y": _ch("gearbox", "casing", "acceleration", "y"),
    "parallel_z": _ch("gearbox", "casing", "acceleration", "z"),
}
LABELS = {  # file name state -> (fault_type, words)
    "health": ("normal", "none"),
    "ball": ("rolling_element", "bearing ball"),
    "inner": ("inner", "bearing inner race"),
    "outer": ("outer", "bearing outer race"),
    "comb": ("inner+outer", "bearing inner race; bearing outer race"),
    "chipped": ("gear", "gear chipped tooth"),
    "miss": ("gear", "gear missing tooth"),
    "root": ("gear", "gear root crack"),
    "surface": ("gear", "gear surface wear"),
}
NAME = re.compile(r"^(?P<cond>[A-Za-z]+)_(?P<speed>\d+)_(?P<load>\d+)$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*.csv")):
        m = NAME.match(path.stem)
        fault_type, detail = LABELS[m["cond"].lower()]
        lines = path.read_bytes().split(b"\n", 16)
        sep = "\t" if b"\t" in lines[16][:200] else ","
        table = pd.read_csv(
            io.BytesIO(lines[16]), sep=sep, header=None, engine="pyarrow", dtype="float64"
        )
        table = table.iloc[:, : len(CHANNELS)]  # drop the empty column of the trailing delimiter
        faults = len(fault_type.split("+"))
        yield {
            "recording_id": f"{path.parent.name}_{path.stem}",
            "native_label": path.stem,
            "fault_type": fault_type,
            "fault_location": "none" if fault_type == "normal" else "+".join(["gearbox"] * faults),
            "fault_detail": detail,
            "subset": path.parent.name,
            "speed_rpm": float(m["speed"]) * 60,
            "load_setting": float(m["load"]),
            "operating_condition": f"{m['speed']}Hz_{m['load']}V",
            "signals": {ch: table[i].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
