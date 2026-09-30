"""NLN-EMP: ``NLN-EMP/Dataset/Dataset/<Vibration|Electric>/Motor-<2|4>/<speed %>/<fault>/
<method>_Motor-<m>_<speed>_time-<fault>-ch<k>.csv``. Each csv: a time column, then one column
per sample (12 s of vibration or 15 s of current/voltage, 20 kHz); column j of every channel
of a folder is one recording. Vibration and electric data come from separate systems."""

import re

import pandas as pd


def _ch(location, quantity, axis="none", unit="g"):
    return {
        "sensor_location": location,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 20000,
    }


VIBRATION = {  # channel number -> name, from the README
    1: ("motor_nde_horizontal", _ch("motor_nde", "acceleration", "horizontal")),
    2: ("motor_de_vertical", _ch("motor_de", "acceleration", "vertical")),
    3: ("motor_de_axial", _ch("motor_de", "acceleration", "axial")),
    4: ("pump_de_horizontal", _ch("pump_de", "acceleration", "horizontal")),
    5: ("pump_nde_vertical", _ch("pump_nde", "acceleration", "vertical")),
}
ELECTRIC = {
    k: (f"{q}_{p}", _ch("motor_supply", q, p, "A" if q == "current" else "V"))
    for k, (q, p) in enumerate(
        [
            ("current", "a"),
            ("current", "b"),
            ("current", "c"),
            ("voltage", "a"),
            ("voltage", "b"),
            ("voltage", "c"),
        ],
        start=1,
    )
}
CHANNELS = dict(v for v in [*VIBRATION.values(), *ELECTRIC.values()])
RPM = {("2", "100"): 1480.0, ("2", "75"): 1110.0, ("2", "50"): 740.0, ("4", "70"): 2070.0}
FAULTS = [  # (folder name pattern, condition, fault_location)
    (r"healthy \d|healthy noise|new motor", "normal", "none"),
    (r"bearing bpfi \d", "inner", "motor_nde_bearing"),
    (r"bearing bpfo \d", "outer", "motor_nde_bearing"),
    (r"bearing bsf", "ball", "motor_nde_bearing"),
    (r"bearing contaminated", "bearing", "motor_nde_bearing"),
    (r"bearing pump \d", "inner+outer", "pump_nde_bearing+pump_nde_bearing"),
    (r"broken rotor bar|stator short \d", "electrical", "motor"),
    (r"impeller \d|cavitation (discharge|suction) \d", "other", "pump"),
    (r"loose foot motor|soft foot \d", "looseness", "motor"),
    (r"loose foot pump", "looseness", "pump"),
    (r"align (angular|parallel|combination) \d", "misalignment", "coupling"),
    (r"bent shaft", "shaft", "motor"),
    (r"coupling \d+D?", "other", "coupling"),
    (r"unbalance motor \d", "unbalance", "coupling_motor_side"),
    (r"unbalance pump \d", "unbalance", "coupling_pump_side"),
]
FOLDER = re.compile(r"^(?P<fault>.*?)(?: (?P<sev>\d+D?))?$")


def _label(fault):
    for pattern, condition, location in FAULTS:
        if re.fullmatch(pattern, fault):
            return condition, location
    raise ValueError(f"unknown fault folder {fault!r}")


def recordings(raw_dir):
    base = next(raw_dir.glob("*/Dataset/Dataset"))
    for method, names in [("Vibration", VIBRATION), ("Electric", ELECTRIC)]:
        for folder in sorted(base.glob(f"{method}/Motor-*/*/*")):
            files = sorted(folder.glob("*-ch*.csv"))
            if not files:
                continue  # a few folders are empty in the published archive
            motor, speed = folder.parent.parent.name.split("-")[1], folder.parent.name
            condition, location = _label(folder.name)
            m = FOLDER.match(folder.name)
            tables = {
                int(f.stem.rsplit("-ch", 1)[1]): pd.read_csv(f, engine="pyarrow").iloc[:, 1:]
                for f in files
            }
            n = {t.shape[1] for t in tables.values()}.pop()
            stem = f"{method}_M{motor}_{speed}_{folder.name.replace(' ', '_')}"
            for j in range(n):
                yield {
                    "recording_id": f"{stem}_{j:02d}",
                    "native_label": folder.name,
                    "condition": condition,
                    "fault_location": location,
                    "severity": m["sev"] if m["sev"] and condition != "normal" else "none",
                    "setup": f"motor_{motor}",
                    "speed_pct": int(speed),
                    "rpm": RPM[(motor, speed)],
                    "measurement": method.lower(),
                    "sample": j,
                    "signals": {names[k][0]: t.iloc[:, j].to_numpy() for k, t in tables.items()},
                }
