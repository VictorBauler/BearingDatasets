"""Ottawa UOEMD-VAFCVS: ``<1_Unloaded|2_Loaded>_Condition/<L1>_<L2>_<speed>_<load>.mat``, one
(420000, 5) matrix ``data``: accelerometer (motor drive end), microphone, accelerometer
(shaft housing near the motor), accelerometer (shaft housing far from the motor),
temperature (motor surface)."""

import re

from bearing_datasets.io import read_mat


def _ch(location, mounting, quantity, unit):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "unit": unit,
        "fs": 42000,
    }


# the shaft housings near and far from the motor hold the rig's bearings
CHANNELS = {
    "accelerometer_motor": _ch("motor_bearing_de", "casing", "acceleration", "m/s^2"),
    "microphone": _ch("ambient", "none", "sound_pressure", "V"),
    "accelerometer_housing_near": _ch("support_bearing_de", "pedestal", "acceleration", "m/s^2"),
    "accelerometer_housing_far": _ch("support_bearing_nde", "pedestal", "acceleration", "m/s^2"),
    "temperature_motor": _ch("motor", "casing", "temperature", "degC"),
}
STATE = {  # code -> (fault_type, fault_location, description)
    "H_H": ("normal", "none", "healthy"),
    "R_U": ("unbalance", "motor_rotor", "rotor unbalance"),
    "R_M": ("misalignment", "motor_rotor", "rotor misalignment"),
    "S_W": ("electrical", "motor_stator", "stator winding fault"),
    "V_U": ("electrical", "motor_supply", "voltage unbalance and single phasing"),
    "B_R": ("shaft", "motor_rotor", "bowed rotor"),
    "K_A": ("electrical", "motor_rotor", "broken rotor bars"),
    "F_B": ("bearing", "motor_bearing", "faulty bearing"),
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
        fault_type, location, detail = STATE[m["state"]]
        operating_condition, profile = SPEED[m["speed"]]
        x = read_mat(path)["data"]
        yield {
            "recording_id": path.stem,
            "native_label": m["state"].replace("_", "-"),
            "fault_type": fault_type,
            "fault_location": location,
            "fault_detail": detail,
            "operating_condition": operating_condition,
            "speed_profile": profile,
            "load_state": "loaded" if m["load"] == "1" else "unloaded",
            "bearing_model": "6205",
            "signals": {ch: x[:, i] for i, ch in enumerate(CHANNELS)},
        }
