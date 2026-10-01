"""Tecnalia bearing: ``Nextmon_MFS_<test>.txt``, same text export as tecnalia_gearbox: a header
(channel legend, Volts/Unit sensitivities) ending with "Time (seconds) and Data Channels", then
time and 16 tab-separated channels at 20.48 kHz (10 s). Tests from the record description."""

import pandas as pd


def _ch(location, mounting, quantity, axis="none"):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": "V",
        "fs": 20480,
    }


# MB ER-12K inboard (test) bearing, manufacturer multipliers per rpm x 60: BPFO 0.0508,
# BPFI 0.0825, BSF 0.0332 (plain); FTF = BPFO / 8 balls
ORDERS = {"bpfo": 3.048, "bpfi": 4.95, "bsf": 1.992, "ftf": 0.381}
CHANNELS = {
    "tacho": _ch("rig_shaft", "shaft", "tachometer"),
    "motor_vertical": _ch("motor", "casing", "acceleration", "vertical"),
    "motor_horizontal": _ch("motor", "casing", "acceleration", "horizontal"),
    "motor_axial": _ch("motor", "casing", "acceleration", "axial"),
    # inboard: the test bearing; outboard: the rig's other bearing
    "inboard_vertical": _ch("test_bearing", "pedestal", "acceleration", "vertical"),
    "inboard_horizontal": _ch("test_bearing", "pedestal", "acceleration", "horizontal"),
    "inboard_axial": _ch("test_bearing", "pedestal", "acceleration", "axial"),
    "outboard_vertical": _ch("support_bearing", "pedestal", "acceleration", "vertical"),
    "outboard_horizontal": _ch("support_bearing", "pedestal", "acceleration", "horizontal"),
    "gearbox_axial": _ch("gearbox", "casing", "acceleration", "axial"),
    "gearbox_horizontal": _ch("gearbox", "casing", "acceleration", "horizontal"),
    "gearbox_vertical": _ch("gearbox", "casing", "acceleration", "vertical"),
    "prox_1": _ch("rig_shaft", "shaft", "displacement"),
    "prox_2": _ch("rig_shaft", "shaft", "displacement"),
    "current_1": _ch("motor_supply", "none", "current", "a"),
    "current_2": _ch("motor_supply", "none", "current", "b"),
}
RAMPS = "14.2-23.4-17.6"
TESTS = {1: ("normal", "50"), 2: ("normal", RAMPS), 3: ("outer", RAMPS), 4: ("outer", "50")}


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("Nextmon_MFS_*.txt")):
        test = int(path.stem.split("_")[-1])
        fault_type, hz = TESTS[test]
        with path.open(encoding="utf-8") as f:
            header = next(i for i, line in enumerate(f) if line.startswith("Time (seconds)"))
        x = pd.read_csv(path, sep="\t", skiprows=header + 1, header=None, engine="c")
        healthy = fault_type == "normal"
        yield {
            "recording_id": f"test{test}",
            "native_label": "healthy" if healthy else "outer race defect",
            "fault_type": fault_type,
            "fault_location": "none" if healthy else "test_bearing",
            "fault_origin": "none" if healthy else "unknown",
            "speed_profile": "varying" if hz == RAMPS else "constant",
            "operating_condition": f"{hz}Hz",
            "bearing_model": "ER-12K",
            **ORDERS,
            "signals": {ch: x.iloc[:, i + 1].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
