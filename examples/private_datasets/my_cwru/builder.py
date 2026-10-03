"""my_cwru (private-dataset example): four CWRU .mat files in a local folder.
``<n>.mat`` holds ``X<nnn>_DE_time``, ``X<nnn>_FE_time`` and ``X<nnn>RPM``; the label of
each file is in FILES."""

from bearing_datasets.io import read_mat

# on the motor casing at the drive end and fan (non-drive) end
CHANNELS = {
    "DE": {"sensor_location": "motor_bearing_de", "sensor_mounting": "casing",
           "quantity": "acceleration", "unit": "g"},
    "FE": {"sensor_location": "motor_bearing_nde", "sensor_mounting": "casing",
           "quantity": "acceleration", "unit": "g"},
}  # fmt: skip
# file: (CWRU label, fault type, sampling rate); faults are on the drive-end bearing
FILES = {
    "97.mat": ("Normal_0", "normal", 48000),
    "105.mat": ("IR007_0", "inner", 12000),
    "118.mat": ("B007_0", "rolling_element", 12000),
    "130.mat": ("OR007@6_0", "outer", 12000),
}


def recordings(raw_dir):
    for file, (label, fault_type, fs) in FILES.items():
        mat = read_mat(raw_dir / file)
        var = f"X{int(file.removesuffix('.mat')):03d}"
        yield {
            "recording_id": label,
            "native_label": label,
            "fault_type": fault_type,
            "fault_location": "none" if fault_type == "normal" else "motor_bearing_de",
            "speed_rpm": float(mat[f"{var}RPM"].squeeze()),
            "source_file": file,
            "fs": fs,
            "signals": {ch: mat[f"{var}_{ch}_time"].ravel() for ch in CHANNELS},
        }
