"""Tecnalia gearbox: ``Nextmon_GPS_<test>.txt``, SpectraQuest-style text export: a header (channel
legend, Volts/Unit sensitivities) ending with "Time (seconds) and Data Channels", then time and
16 tab-separated channels at 20.48 kHz (10 s). Tests from the record description."""

import pandas as pd

from bearing_datasets.bearings import fault_orders


def _ch(location, mounting, quantity, axis="none"):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": "V",
        "fs": 20480,
    }


# ER-16KCL Test Gearbox input bearing (9 balls of 7.94 mm, pitch 38.52 mm, as ER16K in
# ottawa_2018): the record's BPFO 3.572, BPFI 5.43, BSF 2.322 match; its FTF 0.402 does not
# (BPFO = 9 x FTF gives 0.397), so all four are computed from the geometry
ORDERS = fault_orders(9, 7.94, 38.52)
# gearbox and motor are the Test Gearbox and the drive motor; the Load Gearbox and the load
# motor are the rig's loading system (rig)
CHANNELS = {
    "tacho": _ch("motor_shaft", "shaft", "tachometer"),
    "encoder_in": _ch("motor_shaft", "shaft", "encoder"),
    "encoder_out": _ch("rig_shaft", "shaft", "encoder"),
    "torque": _ch("rig_shaft", "shaft", "torque"),
    "current_1": _ch("motor_supply", "none", "current", "a"),
    "current_2": _ch("motor_supply", "none", "current", "b"),
    "drive_motor_vertical": _ch("motor", "casing", "acceleration", "vertical"),
    "drive_motor_axial": _ch("motor", "casing", "acceleration", "axial"),
    "bearing_in_vertical": _ch("gearbox_bearing_input", "casing", "acceleration", "vertical"),
    "bearing_in_axial": _ch("gearbox_bearing_input", "casing", "acceleration", "axial"),
    "bearing_out_horizontal": _ch("gearbox_bearing_output", "casing", "acceleration",
                                  "horizontal"),
    "load_bearing_vertical": _ch("rig", "casing", "acceleration", "vertical"),
    "load_bearing_horizontal": _ch("rig", "casing", "acceleration", "horizontal"),
    "load_motor_vertical": _ch("rig", "casing", "acceleration", "vertical"),
    "bearing_force": _ch("gearbox_bearing_input", "unknown", "force", "axial"),
    "channel16": _ch("unknown", "unknown", "unknown"),
}  # fmt: skip
# Volts/Unit row of the file headers (the same in every file), as in tecnalia_bearing whose
# record says calibrated value = recorded value / Volts/Unit. The torque (0.5) and force
# (0.000498) do not say per what unit.
SENSITIVITY = {
    "tacho": "none", "encoder_in": "none", "encoder_out": "none",
    "current_1": "100 mV/A", "current_2": "100 mV/A",
    "drive_motor_vertical": "100 mV/g", "drive_motor_axial": "98 mV/g",
    "bearing_in_vertical": "101 mV/g", "bearing_in_axial": "101 mV/g",
    "bearing_out_horizontal": "99 mV/g", "load_bearing_vertical": "101 mV/g",
    "load_bearing_horizontal": "95 mV/g", "load_motor_vertical": "94 mV/g",
}  # fmt: skip
for _name, _values in CHANNELS.items():
    _values["sensitivity"] = SENSITIVITY.get(_name, "unknown")
STATE = {  # scenario -> (fault_type, fault_location)
    "baseline": ("normal", "none"),
    "gear": ("gear", "gearbox"),
    "bearing": ("outer", "gearbox_bearing_input"),
    "gear+bearing": ("gear+outer", "gearbox+gearbox_bearing_input"),
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
        fault_type, location = STATE[scenario]
        with path.open(encoding="utf-8") as f:
            header = next(i for i, line in enumerate(f) if line.startswith("Time (seconds)"))
        x = pd.read_csv(path, sep="\t", skiprows=header + 1, header=None, engine="c")
        yield {
            "recording_id": f"test{test:02d}",
            "native_label": scenario,
            "fault_type": fault_type,
            "fault_location": location,
            "operating_condition": operating,
            "speed_profile": "varying" if "speed" in operating else "constant",
            "bearing_model": "ER-16KCL",
            **ORDERS,
            "signals": {ch: x.iloc[:, i + 1].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
