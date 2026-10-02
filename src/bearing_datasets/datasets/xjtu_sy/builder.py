"""XJTU-SY: ``<condition>/BearingX_Y/<n>.csv`` (numeric names, not zero-padded), with the
header ``Horizontal_vibration_signals,Vertical_vibration_signals`` and 32768 rows."""

import pandas as pd

from bearing_datasets.bearings import fault_orders

# LDK UER204 (authors' parameter table): 8 balls of 7.92 mm, pitch diameter 34.55 mm, 0 deg
ORDERS = fault_orders(8, 7.92, 34.55)
CHANNELS = {
    "horizontal": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",
        "quantity": "acceleration",
        "axis": "horizontal",
        "unit": "g",
        "fs": 25600,
    },
    "vertical": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",
        "quantity": "acceleration",
        "axis": "vertical",
        "unit": "g",
        "fs": 25600,
    },
}
CONDITIONS = {"35Hz12kN": (2100.0, 12.0), "37.5Hz11kN": (2250.0, 11.0), "40Hz10kN": (2400.0, 10.0)}
FAILURE = {  # Wang et al. 2020, table of the failed elements
    "Bearing1_1": "outer race",
    "Bearing1_2": "outer race",
    "Bearing1_3": "outer race",
    "Bearing1_4": "cage",
    "Bearing1_5": "inner race; outer race",
    "Bearing2_1": "inner race",
    "Bearing2_2": "outer race",
    "Bearing2_3": "cage",
    "Bearing2_4": "outer race",
    "Bearing2_5": "outer race",
    "Bearing3_1": "outer race",
    "Bearing3_2": "inner race; rolling element; cage; outer race",
    "Bearing3_3": "inner race",
    "Bearing3_4": "inner race",
    "Bearing3_5": "outer race",
}


def recordings(raw_dir):
    base = next((raw_dir / "XJTU-SY_Bearing_Datasets").glob("**/35Hz12kN")).parent
    for condition, (rpm, load) in CONDITIONS.items():
        for run in sorted((base / condition).iterdir()):
            files = sorted(run.glob("*.csv"), key=lambda p: int(p.stem))
            end_of_life = (len(files) - 1) * 60.0
            for i, path in enumerate(files):
                table = pd.read_csv(path, engine="pyarrow", dtype="float64")
                yield {
                    "recording_id": f"{run.name}_{int(path.stem):04d}",
                    "native_label": "unknown",
                    "fault_type": "unknown",
                    "fault_location": "unknown",
                    "speed_rpm": rpm,
                    "load": load,
                    "load_unit": "kN",
                    "bearing_model": "UER204",
                    "run_id": run.name,
                    "time_s": i * 60.0,
                    "rul_s": end_of_life - i * 60.0,
                    "failure": FAILURE[run.name],
                    "operating_condition": condition,
                    "snapshot": i + 1,
                    **ORDERS,
                    "signals": {
                        "horizontal": table.iloc[:, 0].to_numpy(),
                        "vertical": table.iloc[:, 1].to_numpy(),
                    },
                }
