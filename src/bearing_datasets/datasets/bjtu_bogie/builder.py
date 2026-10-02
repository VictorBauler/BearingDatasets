"""BJTU-RAO bogie: ``<health code>/Sample_<k>/data_<group>_<code>_<speed>Hz_<load>kN.csv``
inside a split zip (.z01, .z02, .zip). Each CSV holds the channels of one group
(motor CH1-10, gearbox CH11-16, left axle box CH17-20, right axle box CH21-24).
The zip is read in place (``SplitZip``): nothing is unpacked."""

import io
import re
import struct
import zlib
from collections import defaultdict

import pandas as pd

PARTS = [
    "BJTU_RAO_Bogie_Datasets.z01",
    "BJTU_RAO_Bogie_Datasets.z02",
    "BJTU_RAO_Bogie_Datasets.zip",
]


def _ch(location, mounting, quantity, unit, axis="none"):
    return {
        "sensor_location": location,
        "sensor_mounting": mounting,
        "quantity": quantity,
        "unit": unit,
        "axis": axis,
        "fs": 64000,
    }


def _triaxial(first, location, mounting):
    """Channels CH<first>..CH<first+2>; x/y/z is the channel order (not documented)."""
    return {f"CH{first + i}": _ch(location, mounting, "acceleration", "g", a) for i, a in
            enumerate("xyz")}  # fmt: skip


CHANNELS = {
    **_triaxial(1, "motor_bearing_de", "casing"),
    **_triaxial(4, "motor_bearing_nde", "casing"),
    **{f"CH{i}": _ch("motor_supply", "none", "current", "A", "abc"[i - 7]) for i in (7, 8, 9)},
    "CH10": _ch("motor_shaft", "shaft", "speed", "V"),
    **_triaxial(11, "gearbox_bearing_input", "casing"),
    **_triaxial(14, "gearbox_bearing_output", "casing"),
    **_triaxial(17, "axle_bearing_left", "pedestal"),  # on the axle box end cover
    "CH20": _ch("ambient", "none", "sound_pressure", "Pa"),  # near the left axle box
    **_triaxial(21, "axle_bearing_right", "pedestal"),
    "CH24": _ch("ambient", "none", "sound_pressure", "Pa"),  # near the right axle box
}
# CSV file of each channel's group
GROUP = {f"CH{i}": g for g, chs in [("motor", range(1, 11)), ("gearbox", range(11, 17)),
         ("leftaxlebox", range(17, 21)), ("rightaxlebox", range(21, 25))] for i in chs}  # fmt: skip
# bearing of each channel (designations from the paper)
BEARING_MODEL = {
    ch: "6205" if ch in {f"CH{i}" for i in range(1, 7)} else
    "32305" if ch in {f"CH{i}" for i in range(11, 17)} else
    "352213" if ch in {f"CH{i}" for i in (17, 18, 19, 21, 22, 23)} else "none"
    for ch in CHANNELS
}  # fmt: skip

# health code -> (fault_type, fault_location, words)
CODES = {
    "M1": ("electrical", "motor_stator", "motor stator short circuit"),
    "M2": ("electrical", "motor_rotor", "motor broken rotor bar"),
    "M3": ("bearing", "motor_bearing", "motor bearing fault"),
    "M4": ("shaft", "motor_shaft", "motor bowed shaft"),
    "G1": ("gear", "gearbox", "gear cracked tooth"),
    "G2": ("gear", "gearbox", "gear worn tooth"),
    "G3": ("gear", "gearbox", "gear missing tooth"),
    "G4": ("gear", "gearbox", "gear chipped tooth"),
    "G5": ("inner", "gearbox_bearing", "gearbox bearing inner race"),
    "G6": ("outer", "gearbox_bearing", "gearbox bearing outer race"),
    "G7": ("rolling_element", "gearbox_bearing", "gearbox bearing rolling element"),
    "G8": ("cage", "gearbox_bearing", "gearbox bearing cage"),
    "LA1": ("inner", "axle_bearing_left", "left axle box bearing inner race"),
    "LA2": ("outer", "axle_bearing_left", "left axle box bearing outer race"),
    "LA3": ("rolling_element", "axle_bearing_left", "left axle box bearing rolling element"),
    "LA4": ("cage", "axle_bearing_left", "left axle box bearing cage"),
    "RA1": ("inner", "axle_bearing_right", "right axle box bearing inner race"),
}
# some file names have stray bytes before ".csv" (e.g. "..._0kN\ufffd\ufffd.csv")
FILE = re.compile(
    r"data_(motor|gearbox|leftaxlebox|rightaxlebox)_.+_(\d+)Hz_([+-]?\d+)kN[^/]*\.csv$"
)


class SplitZip:
    """Read members of a split (multi-part) zip without joining or unpacking it.

    The parts are one byte stream cut into pieces, so a member is found at
    (start of its part) + (offset given by the central directory).
    """

    def __init__(self, parts):
        self.files = [open(p, "rb") for p in parts]  # noqa: SIM115 - closed in close()
        self.starts = [0]
        for f in self.files:
            self.starts.append(self.starts[-1] + f.seek(0, 2))
        self.members = self._central_directory()

    def _read(self, pos, n):
        """``n`` bytes at position ``pos`` of the whole stream (may span parts)."""
        out = []
        while n > 0:
            k = max(i for i in range(len(self.files)) if self.starts[i] <= pos)
            self.files[k].seek(pos - self.starts[k])
            chunk = self.files[k].read(min(n, self.starts[k + 1] - pos))
            out.append(chunk)
            pos, n = pos + len(chunk), n - len(chunk)
        return b"".join(out)

    def _central_directory(self):
        size = self.starts[-1]
        tail = self._read(max(0, size - (1 << 20)), min(size, 1 << 20))
        if (k := tail.rfind(b"PK\x06\x06")) >= 0:  # zip64 end of central directory record
            cd_disk, n, cd_size, cd_offset = struct.unpack("<I8xQQQ", tail[k + 20 : k + 56])
        else:  # classic end of central directory record
            k = tail.rfind(b"PK\x05\x06")
            cd_disk, n, cd_size, cd_offset = struct.unpack("<2xH2xHII", tail[k + 4 : k + 20])
        data = self._read(self.starts[cd_disk] + cd_offset, cd_size)
        members, i = {}, 0
        for _ in range(n):
            comp, crc, csize, usize, nlen, xlen, clen, disk, offset = struct.unpack(
                "<10xH4xIIIHHHH6xI", data[i : i + 46]
            )
            name = data[i + 46 : i + 46 + nlen].decode("utf-8", "replace")
            extra = data[i + 46 + nlen : i + 46 + nlen + xlen]
            j = 0
            while j + 4 <= len(extra):  # zip64 extra field: 64-bit values of saturated fields
                tag, length = struct.unpack("<HH", extra[j : j + 4])
                if tag == 1:
                    values = extra[j + 4 : j + 4 + length]
                    if usize == 0xFFFFFFFF:
                        usize, values = struct.unpack("<Q", values[:8])[0], values[8:]
                    if csize == 0xFFFFFFFF:
                        csize, values = struct.unpack("<Q", values[:8])[0], values[8:]
                    if offset == 0xFFFFFFFF:
                        offset, values = struct.unpack("<Q", values[:8])[0], values[8:]
                    if disk == 0xFFFF:
                        disk = struct.unpack("<I", values[:4])[0]
                j += 4 + length
            members[name] = (self.starts[disk] + offset, comp, csize, usize, crc)
            i += 46 + nlen + xlen + clen
        return members

    def read(self, name):
        """Uncompressed bytes of a member (checked against its CRC)."""
        pos, comp, csize, usize, crc = self.members[name]
        nlen, xlen = struct.unpack("<HH", self._read(pos + 26, 4))
        raw = self._read(pos + 30 + nlen + xlen, csize)
        data = zlib.decompress(raw, -15) if comp == 8 else raw
        if len(data) != usize or zlib.crc32(data) != crc:
            raise ValueError(f"corrupt member {name}")
        return data

    def close(self):
        for f in self.files:
            f.close()


def _label(code):
    """``M1_G1+G5_LA0_RA0`` -> (fault_type, fault_location, fault_detail)."""
    faults = [CODES[c] for part in code.split("_") for c in part.split("+") if c in CODES]
    if not faults:
        return "normal", "none", "none"
    return (
        "+".join(f[0] for f in faults),
        "+".join(f[1] for f in faults),
        "; ".join(f[2] for f in faults),
    )


def recordings(raw_dir):
    archive = SplitZip([raw_dir / p for p in PARTS])
    groups = defaultdict(dict)  # (health code, Sample_k) -> {file group: member name}
    for name in archive.members:
        parts = name.split("/")
        if len(parts) == 4 and (m := FILE.search(parts[3])):
            groups[(parts[1], parts[2])][m[1]] = name
    incomplete = {key: sorted(f) for key, f in groups.items() if len(f) != 4}
    if len(groups) != 51 * 9 or incomplete:  # never skip data silently
        raise ValueError(
            f"expected 459 recordings with 4 CSV files each, found {len(groups)}; "
            f"incomplete: {incomplete}"
        )
    try:
        for (code, sample), files in sorted(groups.items()):
            speed, load = FILE.search(files["motor"]).group(2, 3)
            fault_type, location, detail = _label(code)  # from the folder: file names have typos
            tables = {}

            def channel(ch, files=files, tables=tables):
                group = GROUP[ch]
                if group not in tables:  # each CSV is read once per recording
                    data = io.BytesIO(archive.read(files[group]))
                    tables.clear()  # keep one table in memory
                    tables[group] = pd.read_csv(data, engine="pyarrow", dtype="float64")
                return tables[group][ch].to_numpy()

            n = int(sample.split("_")[1])
            yield {
                "recording_id": f"{code}_S{n}",
                "native_label": code,
                "fault_type": fault_type,
                "fault_location": location,
                "fault_detail": detail,
                "speed_rpm": float(speed) * 60,
                "load": float(load),
                "load_unit": "kN",
                "operating_condition": f"{speed}Hz_{load}kN",
                "bearing_model": BEARING_MODEL,
                "signals": {ch: (lambda ch=ch: channel(ch)) for ch in CHANNELS},
            }
    finally:
        archive.close()
