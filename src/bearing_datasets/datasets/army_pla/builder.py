"""Army Engineering University of PLA: ``<Bearing|Parallel Gearbox|Mixed Fault> Dataset/
<state>_<speed>.csv``, speed 1200, 1800, 2400 or 200-2400-200 (rpm). Semicolon separated:
Time(s); CH 1; CH 2; CH 3 (x, y, z of one triaxial accelerometer), 16 kHz, 30 s."""

import pandas as pd

# NU205, 13 rollers on a 38.5 mm pitch (Hou et al., Table 5); from the paper's fault frequencies
# at 20 Hz (BPFI 155.35, BPFO 104.65 Hz) d/D = 0.195
ORDERS = {"bpfo": 5.2325, "bpfi": 7.7675, "bsf": 2.4666, "ftf": 0.4025}
CHANNELS = {
    axis: {
        "sensor_location": "unknown",
        "sensor_mounting": "unknown",
        "quantity": "acceleration",
        "axis": axis,
        "unit": "unknown",
        "fs": 16000,
    }
    for axis in "xyz"
}
BEARING = {
    "IF": "inner",
    "OF": "outer",
    "BF": "rolling_element",
    "CF": "cage",
    "IF+OF": "inner+outer",
}
GEAR = {"gear surface wear", "gear tooth break", "eccentric gear"}
SUBSET = {"Bearing Dataset": "bearing", "Parallel Gearbox Dataset": "gearbox",
          "Mixed Fault Dataset": "mixed"}  # fmt: skip


def _label(state):
    """File name state -> (fault_type, fault_location)."""
    if state.lower() == "normal":
        return "normal", "none"
    if state in BEARING:
        c = BEARING[state]
        return c, "+".join(["test_bearing"] * len(c.split("+")))
    if state in GEAR:
        return "gear", "gearbox"
    race, gear = state.split("+", 1)  # mixed: IF+eccentric gear
    assert gear in GEAR
    return f"{BEARING[race]}+gear", "test_bearing+gearbox"


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("* Dataset/*.csv")):
        state, speed = path.stem.rsplit("_", 1)
        condition, location = _label(state)
        x = pd.read_csv(path, sep=";", usecols=[1, 2, 3], engine="c")
        yield {
            "recording_id": f"{SUBSET[path.parent.name]}_{path.stem.replace(' ', '_')}",
            "native_label": state,
            "fault_type": condition,
            "fault_location": location,
            "fault_origin": "none" if condition == "normal" else "artificial",
            "subset": SUBSET[path.parent.name],
            "operating_condition": f"{speed}rpm",
            "speed_profile": "inc_dec" if "-" in speed else "constant",
            "bearing_model": "NU205",
            **ORDERS,
            "signals": {axis: x.iloc[:, i].to_numpy() for i, axis in enumerate("xyz")},
        }
