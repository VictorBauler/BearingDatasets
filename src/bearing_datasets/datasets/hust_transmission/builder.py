"""HUST transmission system: ``Type<k>/<speed>.csv`` (k = 1-14 health states, speed 20-70 Hz or
0700 for the 0-70-0 Hz run-up/run-down), columns Channel1-4: motor, left bearing housing, right
bearing housing, gearbox (g), 25.6 kHz. Health states from the Readme (table 3)."""

import pandas as pd

from bearing_datasets.bearings import fault_orders


def _ch(location, mounting):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": "acceleration",
        "unit": "g",
        "fs": 25600,
    }


# ER-16K, manufacturer not stated; MB geometry assumed: 9 balls of 7.94 mm, pitch diameter
# 38.52 mm (Huang & Baddour 2018, as ottawa_2018)
ORDERS = fault_orders(9, 7.94, 38.52)
CHANNELS = {
    "motor": _ch("motor", "casing"),
    "bearing_left": _ch("test_bearing_de", "pedestal"),  # left bearing, coupling side
    "bearing_right": _ch("test_bearing_nde", "pedestal"),
    "gearbox": _ch("gearbox", "casing"),
}
STATES = {  # type -> label (component codes, 0 normal, 1 faulty)
    1: "M0_LB0_S0_RB0_RH0_BP0_G0", 2: "M1_LB0_S0_RB0_RH0_BP0_G0", 3: "M0_LB1_S0_RB0_RH0_BP0_G0",
    4: "M0_LB0_S1_RB0_RH0_BP0_G0", 5: "M0_LB0_S0_RB1_RH0_BP0_G0", 6: "M0_LB0_S0_RB0_RH1_BP0_G0",
    7: "M0_LB0_S0_RB0_RH0_BP1_G0", 8: "M0_LB0_S0_RB0_RH0_BP0_G1", 9: "M1_LB1_S1_RB1_RH1_BP1_G1",
    10: "M1_LB1_S0_RB0_RH0_BP0_G1", 11: "M1_LB1_S0_RB0_RH0_BP1_G1", 12: "M1_LB0_S0_RB1_RH0_BP0_G1",
    13: "M1_LB1_S0_RB0_RH1_BP0_G1", 14: "M1_LB1_S0_RB1_RH0_BP0_G1",
}  # fmt: skip
FAULTS = {  # component code -> (fault_type, fault_location)
    "M": ("other", "motor"),  # mechanical fault of the motor
    "LB": ("outer", "test_bearing_de"),  # left bearing
    "S": ("shaft", "rig_shaft"),
    "RB": ("inner", "test_bearing_nde"),  # right bearing
    "RH": ("other", "test_bearing_nde"),  # right bearing housing warping
    "BP": ("other", "rig"),  # belt pulley eccentricity
    "G": ("gear", "gearbox"),  # tooth missing
}


def _label(label):
    parts = [p[:-1] for p in label.split("_") if p.endswith("1")]
    if not parts:
        return "normal", "none"
    return "+".join(FAULTS[p][0] for p in parts), "+".join(FAULTS[p][1] for p in parts)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("Type*/*.csv")):
        state, speed = int(path.parent.name.removeprefix("Type")), path.stem
        label = STATES[state]
        fault_type, location = _label(label)
        varying = speed == "0700"
        x = pd.read_csv(path, engine="c")
        yield {
            "recording_id": f"type{state:02d}_{speed}",
            "native_label": label,
            "fault_type": fault_type,
            "fault_location": location,
            "operating_condition": "0-70-0Hz" if varying else f"{speed}Hz",
            "speed_profile": "inc_dec" if varying else "constant",
            "bearing_model": "ER-16K",
            **ORDERS,
            "signals": {ch: x.iloc[:, i].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
