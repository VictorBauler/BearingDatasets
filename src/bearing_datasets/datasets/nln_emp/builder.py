"""NLN-EMP: ``NLN-EMP/Dataset/Dataset/<Vibration|Electric>/Motor-<2|4>/<speed %>/<fault>/
<method>_Motor-<m>_<speed>_time-<fault>-ch<k>.csv``. Each csv: a time column, then one column
per sample (12 s of vibration or 15 s of current/voltage, 20 kHz); column j of every channel
of a folder is one recording. Vibration and electric data come from separate systems."""

import re

import pandas as pd


def _ch(location, mounting, quantity, axis="none", unit="g"):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 20000,
    }


VIBRATION = {  # channel number -> name, from the README
    1: ("motor_nde_horizontal", _ch("motor_bearing_nde", "casing", "acceleration", "horizontal")),
    2: ("motor_de_vertical", _ch("motor_bearing_de", "casing", "acceleration", "vertical")),
    3: ("motor_de_axial", _ch("motor_bearing_de", "casing", "acceleration", "axial")),
    4: ("pump_de_horizontal", _ch("pump_bearing_de", "casing", "acceleration", "horizontal")),
    5: ("pump_nde_vertical", _ch("pump_bearing_nde", "casing", "acceleration", "vertical")),
}
ELECTRIC = {
    k: (f"{q}_{p}", _ch("motor_supply", "none", q, p, "A" if q == "current" else "V"))
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
FAULTS = [  # (folder name pattern, fault_type, fault_location)
    (r"healthy \d|healthy noise|new motor", "normal", "none"),
    (r"bearing bpfi \d", "inner", "motor_bearing_nde"),
    (r"bearing bpfo \d", "outer", "motor_bearing_nde"),
    (r"bearing bsf", "rolling_element", "motor_bearing_nde"),
    (r"bearing contaminated", "bearing", "motor_bearing_nde"),
    (r"bearing pump \d", "inner+outer", "pump_bearing_nde+pump_bearing_nde"),
    (r"broken rotor bar", "electrical", "motor_rotor"),
    (r"stator short \d", "electrical", "motor_stator"),
    (r"impeller \d", "other", "pump_impeller"),
    (r"cavitation (discharge|suction) \d", "other", "pump"),
    (r"loose foot motor|soft foot \d", "looseness", "motor"),
    (r"loose foot pump", "looseness", "pump"),
    (r"align (angular|parallel|combination) \d", "misalignment", "coupling"),
    (r"bent shaft", "shaft", "motor_shaft"),
    (r"coupling \d+D?", "other", "coupling"),
    (r"unbalance (motor|pump) \d", "unbalance", "coupling"),  # on the coupling, either side
]
FOLDER = re.compile(r"^(?P<fault>.*?)(?: (?P<sev>\d+D?))?$")


def _label(fault):
    for pattern, fault_type, location in FAULTS:
        if re.fullmatch(pattern, fault):
            return fault_type, location
    raise ValueError(f"unknown fault folder {fault!r}")


def _levels(base):
    """Severity level of each fault folder: 1, 2, ... by its number within the fault (2D after
    2); folders without a number are level 1, healthy ones 0."""
    grades = {}
    for folder in base.glob("*/Motor-*/*/*"):
        if (m := FOLDER.match(folder.name))["sev"] and _label(folder.name)[0] != "normal":
            grades.setdefault(m["fault"], set()).add(m["sev"])
    order = {f: sorted(g, key=lambda s: (int(s.rstrip("D")), s)) for f, g in grades.items()}

    def level(name):
        m = FOLDER.match(name)
        if _label(name)[0] == "normal":
            return 0
        return order[m["fault"]].index(m["sev"]) + 1 if m["sev"] else 1

    return level


def recordings(raw_dir):
    base = next(raw_dir.glob("*/Dataset/Dataset"))
    level = _levels(base)
    for method, names in [("Vibration", VIBRATION), ("Electric", ELECTRIC)]:
        for folder in sorted(base.glob(f"{method}/Motor-*/*/*")):
            files = sorted(folder.glob("*-ch*.csv"))
            if not files:
                continue  # a few folders are empty in the published archive
            motor, speed = folder.parent.parent.name.split("-")[1], folder.parent.name
            fault_type, location = _label(folder.name)
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
                    "fault_type": fault_type,
                    "fault_location": location,
                    "fault_severity": m["sev"] if m["sev"] and fault_type != "normal" else "none",
                    "fault_severity_level": level(folder.name),
                    "setup": f"motor_{motor}",
                    "speed_pct": int(speed),
                    "speed_rpm": RPM[(motor, speed)],
                    "measurement": method.lower(),
                    "repetition": j,
                    "signals": {names[k][0]: t.iloc[:, j].to_numpy() for k, t in tables.items()},
                }
