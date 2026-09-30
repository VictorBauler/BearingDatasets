"""Tecnalia gearbox: ``Nextmon_GPS_<test>.txt``, SpectraQuest-style text export: a header (channel
legend, Volts/Unit sensitivities) ending with "Time (seconds) and Data Channels", then time and
16 tab-separated channels at 20.48 kHz (10 s). Tests from the record description."""

import pandas as pd

from bearing_datasets.bearings import fault_orders


def _ch(location, quantity, axis="none"):
    return {
        "sensor_location": location,
        "quantity": quantity,
        "axis": axis,
        "unit": "unknown",
        "fs": 20480,
    }


# ER-16KCL Test Gearbox input bearing (9 balls of 7.94 mm, pitch 38.52 mm, as ER16K in
# ottawa_2018): the record's BPFO 3.572, BPFI 5.43, BSF 2.322 match; its FTF 0.402 does not
# (BPFO = 9 x FTF gives 0.397), so all four are computed from the geometry
ORDERS = fault_orders(9, 7.94, 38.52)
CHANNELS = {
    "tacho": _ch("drive_motor", "tachometer"),
    "encoder_in": _ch("drive_motor", "encoder"),
    "encoder_out": _ch("load_motor", "encoder"),
    "torque": _ch("shaft", "torque"),
    "current_1": _ch("drive_motor", "current", "a"),
    "current_2": _ch("drive_motor", "current", "b"),
    "drive_motor_vertical": _ch("drive_motor", "acceleration", "vertical"),
    "drive_motor_axial": _ch("drive_motor", "acceleration", "axial"),
    "bearing_in_vertical": _ch("test_gearbox_input_bearing", "acceleration", "vertical"),
    "bearing_in_axial": _ch("test_gearbox_input_bearing", "acceleration", "axial"),
    "bearing_out_horizontal": _ch("test_gearbox_output_bearing", "acceleration", "horizontal"),
    "load_bearing_vertical": _ch("load_gearbox_input_bearing", "acceleration", "vertical"),
    "load_bearing_horizontal": _ch("load_gearbox_output_bearing", "acceleration", "horizontal"),
    "load_motor_vertical": _ch("load_motor", "acceleration", "vertical"),
    "bearing_force": _ch("test_gearbox_input_bearing", "force", "axial"),
    "channel16": _ch("unknown", "unknown"),
}
STATE = {  # scenario -> (condition, fault_location)
    "baseline": ("normal", "none"),
    "gear": ("gear", "test_gearbox"),
    "bearing": ("outer", "test_gearbox_input_bearing"),
    "gear+bearing": ("gear+outer", "test_gearbox+test_gearbox_input_bearing"),
}
TESTS = {  # test -> (scenario, operating condition)
    1: ("baseline", "variable speed"), 2: ("baseline", "variable load"),
    3: ("baseline", "stationary"), 4: ("baseline", "variable speed and load"),
    5: ("gear", "variable speed"), 6: ("gear", "variable load"),
    7: ("gear", "variable speed and load"), 8: ("gear", "stationary"),
    10: ("gear+bearing", "variable load"), 11: ("gear+bearing", "variable speed and load"),
    12: ("gear+bearing", "stationary"), 14: ("bearing", "variable load"),
    15: ("bearing", "stationary"), 16: ("bearing", "variable speed and load"),
}  # fmt: skip


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("Nextmon_GPS_*.txt"), key=lambda p: int(p.stem.split("_")[-1])):
        test = int(path.stem.split("_")[-1])
        scenario, operating = TESTS[test]
        condition, location = STATE[scenario]
        with path.open(encoding="utf-8") as f:
            header = next(i for i, line in enumerate(f) if line.startswith("Time (seconds)"))
        x = pd.read_csv(path, sep="\t", skiprows=header + 1, header=None, engine="c")
        yield {
            "recording_id": f"test{test:02d}",
            "native_label": scenario,
            "condition": condition,
            "fault_location": location,
            "operating_condition": operating,
            "speed_profile": "varying" if "speed" in operating else "constant",
            **ORDERS,
            "signals": {ch: x.iloc[:, i + 1].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
