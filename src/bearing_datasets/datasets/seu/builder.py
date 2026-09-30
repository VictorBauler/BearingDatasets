"""SEU: ``<subset>/<condition>_<speed>_<load>.csv``, 16 header lines then 8 columns,
tab-separated (``bearingset/ball_20_0.csv`` uses commas), with a trailing delimiter."""

import io
import re

import pandas as pd


def _ch(location, quantity, axis="none"):
    return {
        "sensor_location": location,
        "quantity": quantity,
        "axis": axis,
        "unit": "unknown",
        "fs": 5120,
    }


CHANNELS = {
    "motor_vibration": _ch("motor", "acceleration"),
    "planetary_x": _ch("planetary_gearbox", "acceleration", "x"),
    "planetary_y": _ch("planetary_gearbox", "acceleration", "y"),
    "planetary_z": _ch("planetary_gearbox", "acceleration", "z"),
    "motor_torque": _ch("motor", "torque"),
    "parallel_x": _ch("parallel_gearbox", "acceleration", "x"),
    "parallel_y": _ch("parallel_gearbox", "acceleration", "y"),
    "parallel_z": _ch("parallel_gearbox", "acceleration", "z"),
}
LABELS = {  # file name condition -> (condition, words)
    "health": ("normal", "none"),
    "ball": ("ball", "bearing ball"),
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
        condition, detail = LABELS[m["cond"].lower()]
        lines = path.read_bytes().split(b"\n", 16)
        sep = "\t" if b"\t" in lines[16][:200] else ","
        table = pd.read_csv(
            io.BytesIO(lines[16]), sep=sep, header=None, engine="pyarrow", dtype="float64"
        )
        table = table.iloc[:, : len(CHANNELS)]  # drop the empty column of the trailing delimiter
        faults = len(condition.split("+"))
        yield {
            "recording_id": f"{path.parent.name}_{path.stem}",
            "native_label": path.stem,
            "condition": condition,
            "fault_location": "none" if condition == "normal" else "+".join(["gearbox"] * faults),
            "fault_detail": detail,
            "subset": path.parent.name,
            "speed_hz": float(m["speed"]),
            "load_setting": float(m["load"]),
            "signals": {ch: table[i].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
