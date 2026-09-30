"""Ottawa UOEMD-VAFCVS: ``<1_Unloaded|2_Loaded>_Condition/<L1>_<L2>_<speed>_<load>.mat``, one
(420000, 5) matrix ``data``: accelerometer (motor drive end), microphone, accelerometer
(shaft housing near the motor), accelerometer (shaft housing far from the motor),
temperature (motor surface)."""

import re

from bearing_datasets.io import read_mat


def _ch(location, quantity, unit):
    return {"sensor_location": location, "quantity": quantity, "unit": unit, "fs": 42000}


CHANNELS = {
    "accelerometer_motor": _ch("motor_de", "acceleration", "m/s^2"),
    "microphone": _ch("motor", "sound_pressure", "V"),
    "accelerometer_housing_near": _ch("housing_near_motor", "acceleration", "m/s^2"),
    "accelerometer_housing_far": _ch("housing_far_from_motor", "acceleration", "m/s^2"),
    "temperature_motor": _ch("motor_de", "temperature", "degC"),
}
STATE = {  # code -> (condition, fault_location, description)
    "H_H": ("normal", "none", "healthy"),
    "R_U": ("unbalance", "rotor", "rotor unbalance"),
    "R_M": ("misalignment", "rotor", "rotor misalignment"),
    "S_W": ("electrical", "stator", "stator winding fault"),
    "V_U": ("electrical", "supply", "voltage unbalance and single phasing"),
    "B_R": ("shaft", "rotor", "bowed rotor"),
    "K_A": ("electrical", "rotor", "broken rotor bars"),
    "F_B": ("bearing", "motor", "faulty bearing"),
}
SPEED = {  # speed code -> (operating_condition, speed_profile)
    "1": ("15Hz", "constant"),
    "2": ("30Hz", "constant"),
    "3": ("45Hz", "constant"),
    "4": ("60Hz", "constant"),
    "5": ("15-45Hz", "increasing"),
    "6": ("30-60Hz", "increasing"),
    "7": ("45-15Hz", "decreasing"),
    "8": ("60-30Hz", "decreasing"),
}
NAME = re.compile(r"^(?P<state>[A-Z]_[A-Z])_(?P<speed>[1-8])_(?P<load>[01])$")


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*/*.mat")):
        m = NAME.match(path.stem)
        condition, location, fault = STATE[m["state"]]
        operating_condition, profile = SPEED[m["speed"]]
        x = read_mat(path)["data"]
        yield {
            "recording_id": path.stem,
            "native_label": m["state"].replace("_", "-"),
            "condition": condition,
            "fault_location": location,
            "fault": fault,
            "operating_condition": operating_condition,
            "speed_profile": profile,
            "load_condition": "loaded" if m["load"] == "1" else "unloaded",
            "signals": {ch: x[:, i] for i, ch in enumerate(CHANNELS)},
        }
