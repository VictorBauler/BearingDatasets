"""KIMM PMSM: ``Multi_Motor_Data/Motor_Data/Motor_Data_<rpm>rpm/Loc<P>_<split>_<Clean|Noise>/
<STATE>/<STATE>_5khz_<rpm>rpm[_noise]_<k>.csv`` with columns timestamp_s, ax, ay, az (in g;
blank lines between rows; one folder writes ``noise1``). Nine files of 500rpm/LocS_Train_Clean
give the time as HH:MM:SS.fff under the header timestamp_ms. State NR, BF, MF (one folder is
lower case), SF or EF."""

import re

import pandas as pd


def _ch(quantity, axis, unit):
    return {"sensor_location": "motor", "sensor_mounting": "casing", "quantity": quantity,
            "axis": axis, "unit": unit, "fs": 5000}  # fmt: skip


CHANNELS = {
    "x": _ch("acceleration", "x", "g"),
    "y": _ch("acceleration", "y", "g"),
    "z": _ch("acceleration", "z", "g"),
    # irregular logger timestamps: fs above is the nominal rate
    "time_s": _ch("time", "none", "s"),
}
STATE = {  # native -> (fault_type, fault_location)
    "NR": ("normal", "none"),
    "BF": ("bearing", "motor_bearing"),
    "MF": ("electrical", "motor_rotor"),  # rotor magnets removed
    "SF": ("other", "motor_stator"),  # stator assembly offset
    "EF": ("other", "motor_shaft"),  # eccentricity at the output shaft
}
NAME = re.compile(r"^(?P<state>[A-Za-z]{2})_5khz_(?P<rpm>\d+)rpm(?P<noise>_noise1?)?_(?P<k>\d)$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("Multi_Motor_Data/Motor_Data/*/*/*/*.csv")):
        m = NAME.match(path.stem)
        state = m["state"].upper()
        folder = path.parent.parent.name
        fault_type, location = STATE[state]
        x = pd.read_csv(path, engine="c")
        t = x.iloc[:, 0]
        if not pd.api.types.is_numeric_dtype(t):
            t = pd.to_timedelta(t).dt.total_seconds()
        yield {
            "recording_id": f"{m['rpm']}rpm_{folder}_{path.stem}",
            "native_label": state,
            "fault_type": fault_type,
            "fault_location": location,
            "fault_origin": "none" if state == "NR" else "artificial",
            "speed_rpm": float(m["rpm"]),
            "sensor_position": folder[3],
            "disturbance": f"noise_{m['k']}" if m["noise"] else "none",
            "kimm_folder": folder,
            "signals": {
                "x": x.ax.to_numpy(),
                "y": x.ay.to_numpy(),
                "z": x.az.to_numpy(),
                "time_s": t.to_numpy("float64"),
            },
        }
