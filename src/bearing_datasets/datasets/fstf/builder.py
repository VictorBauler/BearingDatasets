"""FSTF: ``Datasets <1|2>- ... /Case <k> - <fault>/<name with the speed in rpm>.mat``, one vector
``x`` of sound recorded with a smartphone app (VibroTeak) at 44.1 kHz. Datasets 1: through a
stethoscope; Datasets 2: without. The file names vary; the speed is read as "<n> rpm"."""

import re

from bearing_datasets.io import read_mat

CHANNELS = {
    "sound": {
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",  # through a stethoscope on the housing; none without
        "quantity": "sound_pressure",
        "unit": "normalized",
        "fs": 44100,
    },
}
CASE = {  # case number -> (fault_type, fault_origin)
    "1": ("inner", "artificial"),
    "2": ("outer", "artificial"),
    "3": ("rolling_element", "artificial"),
    "4": ("normal", "none"),
    "5": ("looseness", "real"),  # looseness defect after prolonged operation
    "6": ("inner+outer+rolling_element", "artificial"),
}
RPM = re.compile(r"(\d+)\s*rpm", re.I)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("Datasets*/Case*/*.mat")):
        case = re.match(r"Case (\d)", path.parent.name).group(1)
        fault_type, origin = CASE[case]
        stethoscope = path.parts[-3].startswith("Datasets 1")
        rpm = float(RPM.search(path.stem).group(1))
        parts = fault_type.split("+")
        yield {
            "recording_id": f"{'steth' if stethoscope else 'free'}_case{case}_{int(rpm)}rpm",
            "native_label": path.parent.name,
            "fault_type": fault_type,
            "fault_location": "none"
            if fault_type == "normal"
            else "+".join(["test_bearing"] * len(parts)),
            "fault_origin": origin,
            "speed_rpm": rpm,
            "sensor_mounting": "pedestal" if stethoscope else "none",
            "stethoscope": "yes" if stethoscope else "no",
            "bearing_model": "6004",
            "signals": {"sound": read_mat(path)["x"].ravel()},
        }
