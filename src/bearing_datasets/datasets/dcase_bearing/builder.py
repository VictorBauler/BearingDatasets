"""DCASE 2022 Task 2 development set, bearing: ``dev_bearing/bearing/<train|test>/
section_<ss>_<source|target>_<train|test>_<normal|anomaly>_<nnnn>[_<attributes>].wav``, mono
int16 at 16 kHz, 10 s. Attributes: vel_<n> (rotation velocity), loc_<A-D> (microphone
location), f-n_<A|B> (factory noise)."""

import re

from scipy.io import wavfile

CHANNELS = {
    "microphone": {
        "sensor_location": "ambient",
        "sensor_mounting": "none",
        "quantity": "sound_pressure",
        "unit": "counts",
        "fs": 16000,
    },
}
NAME = re.compile(
    r"^section_(?P<section>\d\d)_(?P<domain>source|target)_(?P<split>train|test)_"
    r"(?P<label>normal|anomaly)_(?P<n>\d+)_?(?P<attr>.*)$"
)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("dev_bearing/bearing/*/*.wav")):
        m = NAME.match(path.stem)
        attrs = dict(zip(*[iter(m["attr"].split("_"))] * 2, strict=True)) if m["attr"] else {}
        _, x = wavfile.read(path)
        anomaly = m["label"] == "anomaly"
        yield {
            "recording_id": path.stem,
            "native_label": m["label"],
            "fault_type": "other" if anomaly else "normal",
            "fault_location": "test_bearing" if anomaly else "none",
            "section": m["section"],
            "domain": m["domain"],
            "dcase_split": m["split"],
            "velocity": attrs.get("vel", "none"),
            "mic_location": attrs.get("loc", "none"),
            "factory_noise": attrs.get("f-n", "none"),
            "signals": {"microphone": x},
        }
