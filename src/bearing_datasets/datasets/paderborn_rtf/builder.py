"""Paderborn run-to-failure: one zip per experiment or several ``B<nn>_part<k>.zip``, holding
``B<nn>/vibrationData/data_B<nn>_M<xxxx>.mat`` (accHorizRear_A, accHorizFrontal_C in V,
measTime) and, once per experiment, ``B<nn>_operatingConditions.csv`` and
``B<nn>_meanTemperatures.csv`` with one row per measurement (row M-1 for file M).
Works with a subset of the zips (``--files``): experiments without their csv files are
skipped, missing measurements are simply absent."""

import re
from datetime import datetime

import pandas as pd

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

# 61806-2RS, dataset document Table 1: 19 balls of 3.18 mm, rolling circle 35.5 mm (0 deg)
ORDERS = fault_orders(19, 3.18, 35.5)
CHANNELS = {
    "acc_A": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",  # rear of the housing
        "quantity": "acceleration",
        "axis": "horizontal",
        "unit": "V",
        "fs": 128000,
    },
    "acc_C": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",  # front of the housing
        "quantity": "acceleration",
        "axis": "horizontal",
        "unit": "V",
        "fs": 128000,
    },
}
FAILURE = {  # defects found after dismantling (description, table 3)
    "B01": "inner race; outer race; ball",
    "B02": "inner race",
    "B03": "inner race",
    "B04": "inner race; ball",
    "B05": "ball",
    "B06": "inner race; ball",
    "B07": "inner race",
    "B08": "inner race; ball",
    "B09": "outer race; ball",
    "B10": "outer race; ball",
    "B11": "inner race; outer race; ball",
    "B12": "inner race; ball",
    "B13": "inner race; ball",
    "B14": "ball",
    "B15": "inner race; ball",
    "B16": "inner race; outer race; ball",
    "B17": "ball",
}
FILE = re.compile(r"^data_(?P<exp>B\d\d)_M(?P<m>\d+)$")


def _csv(raw_dir, exp, kind):
    found = sorted(raw_dir.glob(f"*/{exp}/{exp}_{kind}.csv"))
    return pd.read_csv(found[0]) if found else None


def recordings(raw_dir):
    files = {}
    for path in raw_dir.glob("*/B??/vibrationData/data_B*_M*.mat"):
        m = FILE.match(path.stem)
        files.setdefault(m["exp"], []).append((int(m["m"]), path))
    for exp in sorted(files):
        cond, temp = (
            _csv(raw_dir, exp, "operatingConditions"),
            _csv(raw_dir, exp, "meanTemperatures"),
        )
        if cond is None or temp is None:
            continue  # the part with the csv files was not downloaded
        times = [datetime.strptime(t, "%d-%b-%Y %H:%M:%S") for t in cond["Time"]]
        start, end = times[0], times[-1]
        fs = 128000 if int(exp[1:]) <= 9 else 64000
        for m, path in sorted(files[exp]):
            c, t = cond.iloc[m - 1], temp.iloc[m - 1]
            time_s = (times[m - 1] - start).total_seconds()
            mat = read_mat(path)
            yield {
                "recording_id": path.stem.removeprefix("data_"),
                "native_label": "unknown",
                "fault_type": "unknown",
                "fault_location": "unknown",
                "speed_rpm": float(c["meanAbs_speed / rpm"]),
                "load": float(c["meanAbs_statLoad / N"]),
                "load_unit": "N",
                "bearing_model": "61806-2RS",
                "dynamic_load_peak_n": float(c["peak_dynLoad / N"]),
                "temperature_t1_c": float(t.iloc[1]),
                "temperature_t2_c": float(t.iloc[2]),
                "temperature_room_c": float(t.iloc[3]),
                "run_id": exp,
                "time_s": time_s,
                "rul_s": (end - start).total_seconds() - time_s,
                "failure": FAILURE[exp],
                "fs": fs,
                **ORDERS,
                "signals": {
                    "acc_A": mat["accHorizRear_A"].ravel(),
                    "acc_C": mat["accHorizFrontal_C"].ravel(),
                },
            }
