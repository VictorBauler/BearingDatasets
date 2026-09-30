"""University of Ferrara outer ring defects: ``bearing_dataset/<D1-3><a-c>_<load>N_<Hz>Hz.txt``,
one column of radial acceleration in g, 15 s at 51.2 kHz (25.6 kHz for bearing D2a)."""

import re

import pandas as pd

from bearing_datasets.bearings import fault_orders

# SKF 1205 ETN9, same model and lab as ferrara_rtf (Arpa et al. 2024, Table 2)
ORDERS = fault_orders(12, 7.12, 38.09, 10.2)
CHANNELS = {
    "acceleration": {
        "sensor_location": "test_bearing_case",
        "quantity": "acceleration",
        "axis": "radial",
        "unit": "g",
        "fs": 51200,
    },
}
WIDTH_MM = {  # measured defect widths (ReadMe, table 1)
    "D1a": 0.932, "D1b": 0.907, "D1c": 0.945,
    "D2a": 1.671, "D2b": 1.664, "D2c": 1.658,
    "D3a": 2.507, "D3b": 2.513, "D3c": 2.483,
}  # fmt: skip
NAME = re.compile(r"^(?P<bearing>D[123][abc])_(?P<load>\d+)N_(?P<hz>\d+)Hz$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("bearing_dataset/*.txt")):
        m = NAME.match(path.stem)
        x = pd.read_csv(path, header=None, engine="c").iloc[:, 0].to_numpy()
        yield {
            "recording_id": path.stem,
            "native_label": m["bearing"][:2],
            "condition": "outer",
            "fault_location": "test_bearing",
            "fault_origin": "artificial",
            "fault_size_mm": WIDTH_MM[m["bearing"]],
            "rpm": int(m["hz"]) * 60.0,
            "load": float(m["load"]),
            "load_unit": "N",
            "bearing_id": m["bearing"],
            "fs": 25600 if m["bearing"] == "D2a" else 51200,
            **ORDERS,
            "signals": {"acceleration": x},
        }
