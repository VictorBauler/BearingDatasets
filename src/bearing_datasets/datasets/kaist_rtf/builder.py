"""KAIST run-to-failure: ``Vibration_Bearing_RuntoFailure/LogFile_<YYYY-mm-dd-HH-MM-SS>.csv``,
one per hour, no header, 4 columns: vibration x, vibration y, bearing temperature,
ambient temperature (all at 25.6 kHz)."""

from datetime import datetime

import pandas as pd

from bearing_datasets.bearings import fault_orders

# NSK 6205 (Jung et al. 2024): 9 balls of 7.90 mm, pitch diameter 38.5 mm
ORDERS = fault_orders(9, 7.90, 38.5)
CHANNELS = {
    "vibration_x": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "unknown",
        "quantity": "acceleration",
        "axis": "x",
        "unit": "unknown",
        "fs": 25600,
    },
    "vibration_y": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "unknown",
        "quantity": "acceleration",
        "axis": "y",
        "unit": "unknown",
        "fs": 25600,
    },
    "temperature_bearing": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "unknown",
        "quantity": "temperature",
        "axis": "none",
        "unit": "degC",
        "fs": 25600,
    },
    "temperature_ambient": {
        "sensor_location": "ambient",
        "sensor_mounting": "none",
        "quantity": "temperature",
        "axis": "none",
        "unit": "degC",
        "fs": 25600,
    },
}


def recordings(raw_dir):
    files = sorted(raw_dir.glob("Vibration_Bearing_RuntoFailure/**/LogFile_*.csv"))
    times = [datetime.strptime(p.stem[len("LogFile_") :], "%Y-%m-%d-%H-%M-%S") for p in files]
    end_of_life = (times[-1] - times[0]).total_seconds()
    for path, t in zip(files, times, strict=True):
        time_s = (t - times[0]).total_seconds()
        table = pd.read_csv(path, header=None, engine="pyarrow", dtype="float64")
        yield {
            "recording_id": path.stem,
            "native_label": "unknown",
            "fault_type": "unknown",
            "fault_location": "unknown",
            "speed_rpm": 1775.0,
            "load": 5.88,
            "load_unit": "kN",
            "bearing_model": "6205",
            "run_id": "run1",
            "time_s": time_s,
            "rul_s": end_of_life - time_s,
            **ORDERS,
            "signals": {ch: table[i].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
