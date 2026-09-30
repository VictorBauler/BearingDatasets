"""UPM CITEF spherical roller bearing databases (FAG 22205E1KC3), three Zenodo records in one
folder: ``<n>_<rpm>_S1_<component>_F<level>_R<repeat>.mat`` with ``Fs`` and ``Rod_1`` (housing
of the faulty bearing), ``Rod_2`` (other housing), ``Rod_3`` (tightening tower). Component: RE
(rolling element; 2020), ORRE (outer race + rolling elements; 2021, 3-digit numbers), EE
(healthy), OR, IR, RE (2023, the files listed in STUDY_2023)."""

import re

from bearing_datasets.io import read_mat

# FAG 22205E1KC3, official Schaeffler values (Sensors 2020, 20, 3493, Table 1); its BSF 5.4030
# is 2 x BSF
ORDERS = {"bpfo": 6.1852, "bpfi": 8.8148, "bsf": 5.4030 / 2, "ftf": 0.4123}
CHANNELS = {
    "Rod_1": {"sensor_location": "test_bearing_housing", "quantity": "acceleration"},
    "Rod_2": {"sensor_location": "support_bearing_housing", "quantity": "acceleration"},
    "Rod_3": {"sensor_location": "tightening_tower", "quantity": "acceleration"},
}
for _c in CHANNELS.values():
    _c["unit"] = "unknown"
STUDY_2023 = {
    "01_500_S1_EE_F0_R1",
    "02_500_S1_EE_F0_R2",
    "03_500_S1_EE_F0_R3",
    "04_500_S1_OR_F1_R1",
    "05_500_S1_IR_F1_R1",
    "06_500_S1_RE_F1_R1",
    "07_500_S1_OR_F2_R1",
    "08_500_S1_IR_F2_R1",
    "09_500_S1_RE_F2_R1",
    "10_500_S1_OR_F3_R1",
    "11_500_S1_IR_F3_R1",
    "12_500_S1_RE_F3_R1",
    "13_500_S1_OR_F4_R1",
    "14_500_S1_IR_F4_R1",
    "15_500_S1_RE_F4_R1",
}
DEPTH_MM = {  # study -> component -> depth of fault levels F1-F4 (from the READ_ME files)
    "2020": {"RE": (0.006, 0.014, 0.019, 0.027)},
    "2021": {"RE": (0.006, 0.014, 0.019, 0.027), "OR": (0.007, 0.013, 0.02, 0.028)},
    "2023": {
        "RE": (0.007, 0.013, 0.021, 0.029),
        "IR": (0.007, 0.016, 0.024, 0.031),
        "OR": (0.008, 0.016, 0.024, 0.032),
    },
}
LOAD_KN = {"2020": 1.4, "2021": 1.4, "2023": 3.92}  # 2023: 400 kg
NAME = re.compile(
    r"^(?P<n>\d+)_(?P<rpm>\d+)_S1_(?P<comp>RE|ORRE|EE|OR|IR)_F(?P<f>[0-4])_R(?P<r>\d)$"
)


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.mat")):
        m = NAME.match(path.stem)
        study = "2023" if path.stem in STUDY_2023 else "2021" if m["comp"] == "ORRE" else "2020"
        level = int(m["f"])
        parts = ["OR", "RE"] if m["comp"] == "ORRE" else [m["comp"]]
        depth = {c: 0.0 for c in ("OR", "IR", "RE")}
        if level:
            for c in parts:
                depth[c] = DEPTH_MM[study][c][level - 1]
        names = {"OR": "outer", "IR": "inner", "RE": "ball"}
        condition = "+".join(names[c] for c in parts) if level else "normal"
        mat = read_mat(path)
        yield {
            "recording_id": f"{study}_{path.stem}",
            "native_label": f"{m['comp']}_F{level}",
            "condition": condition,
            "fault_location": "+".join(["test_bearing"] * len(parts)) if level else "none",
            "fault_origin": "artificial" if level else "none",
            "severity": f"F{level}",
            "depth_or_mm": depth["OR"],
            "depth_ir_mm": depth["IR"],
            "depth_re_mm": depth["RE"],
            "rpm": float(m["rpm"]),
            "load": LOAD_KN[study],
            "load_unit": "kN",
            "study": study,
            "repetition": int(m["r"]),
            "fs": float(mat["Fs"].item()),
            **ORDERS,
            "signals": {ch: mat[ch].ravel() for ch in CHANNELS},
        }
