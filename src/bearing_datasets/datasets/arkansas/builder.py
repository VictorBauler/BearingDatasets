"""University of Arkansas: ``Fault data split <25|50|75>/.../<scenario> Trial <n>.csv``, a 4-line
header (Timestamp, Interval, Channel name, Unit per channel) then (time, value) column pairs for
9 channels at 6.4 kHz (10 s). Scenario names join up to two faults with " & ": "Bearing (k)
<ball|inner|outer|combination>" (also written "Bearing (k) Fault (...)"), "Shaft Fault
(<where> bent)" or "No Fault"; spelling varies."""

import re

import pandas as pd


def _ch(location, quantity, axis="none", unit="g"):
    return {
        "sensor_location": location,
        "quantity": quantity,
        "axis": axis,
        "unit": unit,
        "fs": 6400,
    }


CHANNELS = {
    "tachometer": _ch("shaft", "tachometer", unit="V"),
    "motor": _ch("motor", "acceleration"),
    "bearing1_z": _ch("bearing_1", "acceleration", "z"),
    "bearing1_y": _ch("bearing_1", "acceleration", "y"),
    "bearing1_x": _ch("bearing_1", "acceleration", "x"),
    "bearing2_z": _ch("bearing_2", "acceleration", "z"),
    "bearing2_y": _ch("bearing_2", "acceleration", "y"),
    "bearing2_x": _ch("bearing_2", "acceleration", "x"),
    "gearbox": _ch("gearbox", "acceleration"),
}
BEARING_FAULT = {"ball": "ball", "inner": "inner", "outer": "outer", "comb": "bearing"}
NAME = re.compile(r"^(?P<scenario>.+?) Trial (?P<trial>\d+)$")


def _part(text, last_bearing):
    """One fault of a scenario name -> (condition, fault_location, bearing number)."""
    t = text.lower()
    if t.startswith("shaft"):
        where = "coupling_end" if "coupling" in t else "center"
        return "shaft", f"shaft_bent_{where}", last_bearing
    m = re.search(r"bearing \((\d)\)", t)
    k = m.group(1) if m else last_bearing
    kind = next(v for key, v in BEARING_FAULT.items() if key in t)
    return kind, f"bearing_{k}", k


def _label(scenario):
    if scenario.startswith("No Fault"):  # also "No Fault 50", "No Fault 75"
        return "normal", "none"
    parts, k = [], None
    for text in scenario.split(" & "):
        c, loc, k = _part(text, k)
        parts.append((c, loc))
    return "+".join(c for c, _ in parts), "+".join(loc for _, loc in parts)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("Fault data split */*/*.csv")):
        m = NAME.match(path.stem)
        scenario = " ".join(m["scenario"].split())
        slug = re.sub(r"[^A-Za-z0-9]+", "_", scenario).strip("_")
        condition, location = _label(scenario)
        speed = path.parent.parent.name.rsplit(" ", 1)[1]
        x = pd.read_csv(path, skiprows=4, header=None, engine="c").iloc[:, 1::2]
        yield {
            "recording_id": f"s{speed}_{slug}_{int(m['trial']):02d}",
            "native_label": scenario,
            "condition": condition,
            "fault_location": location,
            "fault_origin": "none" if condition == "normal" else "artificial",
            "speed_setting": int(speed),
            "trial": int(m["trial"]),
            "signals": {ch: x.iloc[:, i].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
