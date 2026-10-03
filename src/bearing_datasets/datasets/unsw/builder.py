"""UNSW run-to-failure: ``Test <t>/Test <t>/<6Hz|Multiple speeds>/vib_<shaft cycles>_<Hz>.mat``
with Fs, accH, accV, enc1, enc2, loadCell, tacho (all in V). The 6 Hz samples of
``Multiple speeds`` are copies of files in ``6Hz`` and are skipped."""

import re

from bearing_datasets.io import read_mat

# "Read me for data description.docx": accelerometers 10 mV/ms-2, load cell 2.8 kN/V
SENSITIVITY = {"acceleration": "10 mV/(m/s^2)", "force": "357.1 mV/kN"}


def _ch(location, mounting, quantity, axis="none"):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "axis": axis,
        "unit": "V",
        "sensitivity": SENSITIVITY.get(quantity, "none"),
    }


CHANNELS = {
    "accH": _ch("test_bearing", "unknown", "acceleration", "horizontal"),
    "accV": _ch("test_bearing", "unknown", "acceleration", "vertical"),
    "enc1": _ch("rig_shaft", "shaft", "encoder"),
    "enc2": _ch("rig_shaft", "shaft", "encoder"),
    "loadCell": _ch("test_bearing", "unknown", "force"),
    "tacho": _ch("rig_shaft", "shaft", "tachometer"),
}
NAME = re.compile(r"^vib_(?P<cycles>\d+)_(?P<hz>\d+)$")


def recordings(raw_dir):
    for test in sorted(raw_dir.glob("Test ?")):
        files = sorted(test.glob("*/6Hz/*.mat")) + [
            p for p in sorted(test.glob("*/Multiple speeds/*.mat")) if not p.stem.endswith("_06")
        ]
        end_of_life = max(int(NAME.match(p.stem)["cycles"]) for p in files)
        for path in sorted(files, key=lambda p: p.stem):
            m = NAME.match(path.stem)
            cycles, hz = int(m["cycles"]), int(m["hz"])
            mat = read_mat(path)
            yield {
                "recording_id": f"{test.name.replace(' ', '')}_{path.stem}",
                "native_label": "unknown",
                "fault_type": "unknown",
                "fault_location": "unknown",
                "speed_rpm": hz * 60.0,
                "run_id": test.name,
                "shaft_cycles": cycles,
                "rul_cycles": end_of_life - cycles,
                "fs": float(mat["Fs"].item()),
                "signals": {ch: mat[ch].ravel() for ch in CHANNELS},
            }
