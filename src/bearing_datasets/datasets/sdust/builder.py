"""SDUST bearing subset: ``轴承数据集/<state>/<state> <speed> <load>[ <repeat>].mat``, e.g.
``IF0.2 1000 20.mat`` or ``OF0.6 1000~2000 40.mat`` (speed varying between 1000 and 2000
rpm; some files write ``1000-2000``). Simcenter Test.Lab ``Signal`` struct, 6 columns at
25.6 kHz, named in the file ``zcjshang:+Z/+Y/+X`` and ``zcjxia:+Z/+Y/+X`` (upper and lower
sensor)."""

import re

from bearing_datasets.bearings import fault_orders
from bearing_datasets.io import read_mat

# 6205, dataset PDF Table 1: 9 balls of 7.938 mm, 0 deg; no pitch diameter given: SKF 6205's
# 39.04 mm
ORDERS = fault_orders(9, 7.938, 39.04)
CHANNELS = {
    f"{pos}_{axis.lower()}": {
        "sensor_location": f"sensor_{pos}",
        "quantity": "acceleration",
        "axis": axis.lower(),
        "unit": "unknown",
        "fs": 25600,
    }
    for pos in ("upper", "lower")
    for axis in "ZYX"
}
CONDITION = {"NC": "normal", "IF": "inner", "OF": "outer", "RF": "ball"}
NAME = re.compile(
    r"^(?P<state>NC|IF|OF|RF)(?P<size>[0-9.]*) (?P<speed>\d+(?:[~-]\d+)?) (?P<load>\d+)"
    r"(?: (?P<rep>\d))?$"
)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*/*.mat")):
        m = NAME.match(path.stem)
        signal = read_mat(path)["Signal"][0, 0]
        x = signal["y_values"]["values"][0, 0]
        speed = m["speed"].replace("~", "-")
        healthy = m["state"] == "NC"
        yield {
            "recording_id": path.stem.replace(" ", "_").replace("~", "-"),
            "native_label": m["state"] + m["size"],
            "condition": CONDITION[m["state"]],
            "fault_location": "none" if healthy else "test_bearing",
            "fault_origin": "none" if healthy else "artificial",
            "fault_size_mm": 0.0 if healthy else float(m["size"]),
            "operating_condition": f"{speed}rpm",
            "speed_profile": "varying" if "-" in speed else "constant",
            "load": float(m["load"]),
            "load_unit": "N",
            "repetition": m["rep"] or "1",
            **ORDERS,
            "signals": {ch: x[:, i] for i, ch in enumerate(CHANNELS)},
        }
