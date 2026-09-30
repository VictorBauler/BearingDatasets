"""JUST slewing bearing: ``condition<k>/<folder>/<date>-<N|I|O|B1>-<rpm>rpm-<load>N-<rep>.csv``
(the folder name is a garbled Chinese "condition k"). Columns: Time (s), AI 1-6 (m/s2), AI 7
(dB), 50 kHz, ~61 s."""

import re

import pandas as pd


def _ch(quantity, unit):
    return {"sensor_location": "unknown", "quantity": quantity, "unit": unit, "fs": 50000}


CHANNELS = {**{f"ai{i}": _ch("acceleration", "m/s^2") for i in range(1, 7)},
            "ai7_acoustic": _ch("sound_pressure", "dB")}  # fmt: skip
STATE = {"N": "normal", "I": "inner", "O": "outer", "B1": "ball"}
NAME = re.compile(r"^\d+-(?P<state>N|I|O|B1)-(?P<rpm>[\d.]+)rpm-(?P<load>[\d.]+)N-(?P<rep>\d+)$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("condition*/*/*.csv")):
        m = NAME.match(path.stem)
        condition = STATE[m["state"]]
        x = pd.read_csv(path, engine="c").iloc[:, 1:8]
        yield {
            "recording_id": f"{m['state']}_{m['rpm']}rpm_{m['load']}N_{m['rep']}",
            "native_label": m["state"],
            "condition": condition,
            "fault_location": "none" if condition == "normal" else "slewing_bearing",
            "fault_origin": "none" if condition == "normal" else "artificial",
            "rpm": float(m["rpm"]),
            "load": float(m["load"]),
            "load_unit": "N (as in the file names)",
            "repetition": int(m["rep"]),
            "signals": {ch: x.iloc[:, i].to_numpy() for i, ch in enumerate(CHANNELS)},
        }
