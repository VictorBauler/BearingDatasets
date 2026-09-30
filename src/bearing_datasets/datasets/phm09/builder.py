"""PHM09: ``gearset/raw/<case>/<case>_<speed>hz_<High|Low>_<rep>.txt`` in gearset.zip,
3 whitespace-separated columns: input accelerometer, output accelerometer, tachometer."""

import io
import re
import zipfile

import numpy as np

from bearing_datasets.bearings import fault_orders

# official apparatus page: MB ER-10K bearings, 8 balls of 0.3125 in, pitch 1.319 in
ORDERS = fault_orders(8, 0.3125, 1.319)
CHANNELS = {
    "input_accelerometer": {
        "sensor_location": "gearbox_input_side",
        "quantity": "acceleration",
        "axis": "none",
        "unit": "V",
        "fs": 200000 / 3,
    },
    "output_accelerometer": {
        "sensor_location": "gearbox_output_side",
        "quantity": "acceleration",
        "axis": "none",
        "unit": "V",
        "fs": 200000 / 3,
    },
    "tachometer": {
        "sensor_location": "input_shaft",
        "quantity": "tachometer",
        "axis": "none",
        "unit": "V",
        "fs": 200000 / 3,
    },
}
IN, ID, OUT = "input_shaft", "idler_shaft", "output_shaft"
# case -> faults (condition, location, words); "IS:IS" = input shaft, input-side bearing
CASES = {
    "spur 1": [],
    "spur 2": [("gear", IN, "32T gear chipped"), ("gear", ID, "48T gear eccentric")],
    "spur 3": [("gear", ID, "48T gear eccentric")],
    "spur 4": [
        ("gear", ID, "48T gear eccentric"),
        ("gear", OUT, "80T gear broken"),
        ("ball", IN, "bearing IS:IS ball"),
    ],
    "spur 5": [
        ("gear", IN, "32T gear chipped"),
        ("gear", ID, "48T gear eccentric"),
        ("gear", OUT, "80T gear broken"),
        ("inner", IN, "bearing IS:IS inner race"),
        ("ball", ID, "bearing ID:IS ball"),
        ("outer", OUT, "bearing OS:IS outer race"),
    ],
    "spur 6": [
        ("gear", OUT, "80T gear broken"),
        ("inner", IN, "bearing IS:IS inner race"),
        ("ball", ID, "bearing ID:IS ball"),
        ("outer", OUT, "bearing OS:IS outer race"),
        ("unbalance", IN, "input shaft unbalance"),
    ],
    "spur 7": [
        ("inner", IN, "bearing IS:IS inner race"),
        ("shaft", OUT, "output shaft keyway sheared"),
    ],
    "spur 8": [
        ("ball", ID, "bearing ID:IS ball"),
        ("outer", OUT, "bearing OS:IS outer race"),
        ("unbalance", IN, "input shaft unbalance"),
    ],
    "helical 1": [],
    "helical 2": [("gear", ID, "24T gear chipped")],
    "helical 3": [
        ("gear", ID, "24T gear broken"),
        ("bearing", IN, "bearing IS:OS combination"),
        ("inner", ID, "bearing ID:OS inner race"),
        ("shaft", IN, "input shaft bent"),
    ],
    "helical 4": [
        ("bearing", IN, "bearing IS:OS combination"),
        ("ball", ID, "bearing ID:OS ball"),
        ("unbalance", IN, "input shaft unbalance"),
    ],
    "helical 5": [("gear", ID, "24T gear broken"), ("inner", ID, "bearing ID:OS inner race")],
    "helical 6": [
        ("gear", OUT, "40T gear broken"),
        ("inner", IN, "bearing IS:IS inner race"),
        ("ball", ID, "bearing ID:IS ball"),
        ("outer", OUT, "bearing OS:IS outer race"),
        ("shaft", IN, "input shaft bent"),
    ],
}
NAME = re.compile(r"^(?P<case>(spur|helical) \d)_(?P<speed>\d+)hz_(?P<load>High|Low)_(?P<rep>\d)$")


def recordings(raw_dir):
    with zipfile.ZipFile(raw_dir / "gearset.zip") as zf:
        names = sorted(
            n for n in zf.namelist() if n.startswith("gearset/raw/") and n.endswith(".txt")
        )
        if len(names) != 280:  # never skip data silently
            raise ValueError(f"expected 280 runs in gearset/raw, found {len(names)}")
        for name in names:
            m = NAME.match(name.rsplit("/", 1)[1].removesuffix(".txt"))
            faults = CASES[m["case"]]
            table = np.loadtxt(io.BytesIO(zf.read(name)), dtype=np.float64, ndmin=2)
            yield {
                "recording_id": name.rsplit("/", 1)[1].removesuffix(".txt").replace(" ", ""),
                "native_label": m["case"],
                "condition": "+".join(f[0] for f in faults) or "normal",
                "fault_location": "+".join(f[1] for f in faults) or "none",
                "fault_detail": "; ".join(f[2] for f in faults) or "none",
                "gear_type": m["case"].split()[0],
                "speed_hz": float(m["speed"]),
                "rpm": float(m["speed"]) * 60,
                "load_level": m["load"],
                "repeat": int(m["rep"]),
                **ORDERS,
                "signals": {ch: table[:, i] for i, ch in enumerate(CHANNELS)},
            }
