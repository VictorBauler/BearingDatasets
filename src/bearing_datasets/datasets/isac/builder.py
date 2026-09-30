"""ISAC Lab: ``RMF_Dataset/<Normal|Ball Fault|Outer Race Fault|Unbalanced Fault>/Acquisition*.csv``
(Advantech USB-4711A log): a 24-line header with the time step (dt), then X_Value and AI Channel
0-11 in V. The channel-to-sensor mapping is not documented. Names: Acquisition<Hz>hz<n>
(healthy), Acquisition_out_<bearing>_<Hz>hz, Acquisition_ballfault_<bearing>_<Hz>hz,
Acquisition_un_<disk>[_<disk>]_<Hz>hz."""

import re

import pandas as pd

CHANNELS = {
    f"ai{i}": {"sensor_location": "unknown", "quantity": "unknown", "unit": "V", "fs": 10040}
    for i in range(12)
}
NAME = re.compile(
    r"^Acquisition(?:(?P<hz0>\d+)hz(?P<rep>\d)|_(?P<kind>out|ballfault|un)_(?P<where>[\d_]+?)_(?P<hz>\d+)hz)$"
)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/RMF_Dataset/*/Acquisition*.csv")):
        m = NAME.match(path.stem)
        with path.open(encoding="utf-8") as f:
            head = [next(f) for _ in range(24)]
        dt = float(next(h for h in head if h.startswith("dt,")).split(",")[1].rstrip("s\n"))
        x = pd.read_csv(path, skiprows=24, engine="c").iloc[:, 1:13]
        if m["hz0"]:
            label = {"condition": "normal", "fault_location": "none", "hz": m["hz0"]}
        elif m["kind"] == "un":
            disks = m["where"].split("_")
            where = f"disk_{disks[0]}" if len(disks) == 1 else "disks_" + "_and_".join(disks)
            label = {"condition": "unbalance", "fault_location": where, "hz": m["hz"]}
        else:
            race = "outer" if m["kind"] == "out" else "ball"
            label = {"condition": race, "fault_location": f"bearing_{m['where']}", "hz": m["hz"]}
        yield {
            "recording_id": path.stem,
            "native_label": path.stem.removeprefix("Acquisition").strip("_") or path.stem,
            "condition": label["condition"],
            "fault_location": label["fault_location"],
            "rpm": int(label["hz"]) * 60.0,
            "fs": round(1 / dt, 2),
            "signals": {f"ai{i}": x.iloc[:, i].to_numpy() for i in range(12)},
        }
