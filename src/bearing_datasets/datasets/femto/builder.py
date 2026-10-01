"""FEMTO: ``<set>/BearingX_Y/acc_NNNNN.csv`` (hour, minute, second, microsecond, horizontal,
vertical; 2560 rows) and ``temp_NNNNN.csv`` (hour, minute, second, tenth, temperature;
600 rows). Some files use ";" instead of ",". Only the full runs are read (learning set
and Full_Test_Set); the truncated Test_set only tells which snapshots were official."""

import numpy as np

from bearing_datasets.bearings import fault_orders

# PHM 2012 challenge document, App. A.1: 13 balls of 3.5 mm, pitch diameter 25.6 mm (angle
# not stated: 0 deg)
ORDERS = fault_orders(13, 3.5, 25.6)
# accelerometers radially on the bearing's outer ring; the temperature probe in a hole close
# to it (Nectoux et al. 2012)
CHANNELS = {
    "horizontal": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "outer_ring",
        "quantity": "acceleration",
        "axis": "horizontal",
        "unit": "g",
        "fs": 25600,
    },
    "vertical": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "outer_ring",
        "quantity": "acceleration",
        "axis": "vertical",
        "unit": "g",
        "fs": 25600,
    },
    "temperature": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "outer_ring",
        "quantity": "temperature",
        "axis": "none",
        "unit": "degC",
        "fs": 10,
    },
}
CONDITIONS = {"1": (1800.0, 4000.0), "2": (1650.0, 4200.0), "3": (1500.0, 5000.0)}
SETS = {"Training_set/Learning_set": "learning", "Validation_Set/Full_Test_Set": "test"}
PERIOD = {"acc": 10.0, "temp": 60.0}  # s between snapshots


def _read(path):
    delimiter = ";" if b";" in path.read_bytes()[:200] else ","
    return np.loadtxt(path, delimiter=delimiter, dtype=np.float64, ndmin=2)


def recordings(raw_dir):
    base = raw_dir / "10. FEMTO Bearing" / "10. FEMTO Bearing" / "FEMTOBearingDataSet"
    for folder, official in SETS.items():
        for run in sorted((base / folder).iterdir()):
            truncated = base / "Test_set" / "Test_set" / run.name
            acc_files = sorted(run.glob("acc_*.csv"))
            end_of_life = (len(acc_files) - 1) * PERIOD["acc"]
            rpm, load = CONDITIONS[run.name[7]]  # "Bearing1_3" -> condition 1
            for kind in ("acc", "temp"):
                files = acc_files if kind == "acc" else sorted(run.glob("temp_*.csv"))
                n_official = len(list(truncated.glob(f"{kind}_*.csv")))
                for i, path in enumerate(files):
                    table = _read(path)
                    signals = (
                        {"horizontal": table[:, 4], "vertical": table[:, 5]}
                        if kind == "acc"
                        else {"temperature": table[:, 4]}
                    )
                    time_s = i * PERIOD[kind]
                    yield {
                        "recording_id": f"{run.name}_{path.stem}",
                        "native_label": "unknown",
                        "fault_type": "unknown",
                        "fault_location": "unknown",
                        "speed_rpm": rpm,
                        "load": load,
                        "load_unit": "N",
                        "run_id": run.name,
                        "time_s": time_s,
                        "rul_s": end_of_life - time_s,
                        "operating_condition": run.name[7],
                        "official_set": official
                        if official == "learning"
                        else ("test" if i < n_official else "hidden"),
                        "snapshot": i + 1,
                        **ORDERS,
                        "signals": signals,
                    }
