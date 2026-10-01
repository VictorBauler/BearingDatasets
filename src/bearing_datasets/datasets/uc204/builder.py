"""UC204 outer race faults: ``<Normal_<load>Hp | OR_<load>Hp_<size>mm>/<name>_<n>.txt``, 10
recordings per condition, one column of acceleration (tab-indented text), 3.2 kHz, 10 s. Loads
025, 04/040, 06/060 = 0.25, 0.4, 0.6 hp; sizes 018-072 = 0.18-0.72 mm (groove length)."""

import re

import pandas as pd

CHANNELS = {
    "acceleration": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",
        "quantity": "acceleration",
        "unit": "unknown",
        "fs": 3200,
    },
}
FOLDER = re.compile(r"^(?P<state>Normal|OR)_(?P<load>\d+)Hp(?:_(?P<size>\d+)mm)?$")
SIZES = ["018", "036", "054", "072"]  # groove length, 0.01 mm: levels 1-4
LOAD_HP = {"025": 0.25, "04": 0.4, "040": 0.4, "06": 0.6, "060": 0.6}


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*.txt")):
        m = FOLDER.match(path.parent.name)
        healthy = m["state"] == "Normal"
        n = int(path.stem.rsplit("_", 1)[1])
        x = pd.read_csv(path, header=None, sep=r"\s+", engine="python").iloc[:, 0].to_numpy()
        yield {
            "recording_id": f"{path.parent.name}_{n:02d}",
            "native_label": path.parent.name,
            "fault_type": "normal" if healthy else "outer",
            "fault_location": "none" if healthy else "test_bearing",
            "fault_origin": "none" if healthy else "artificial",
            "fault_size_mm": 0.0 if healthy else int(m["size"]) / 100,
            "fault_severity": "none" if healthy else f"{int(m['size']) / 100} mm",
            "fault_severity_level": 0 if healthy else SIZES.index(m["size"]) + 1,
            "bearing_model": "UC204",
            "speed_rpm": 1500.0,
            "load": LOAD_HP[m["load"]],
            "load_unit": "hp",
            "signals": {"acceleration": x},
        }
