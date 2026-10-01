"""IMS: ``<n>_test/<YYYY.MM.DD.hh.mm.ss>``, tab-separated text without header, 20480 rows,
8 columns in test 1 (x/y per bearing) and 4 in tests 2 and 3."""

from datetime import datetime

import pandas as pd

from bearing_datasets.bearings import fault_orders


def _ch(axis="none"):
    return {  # all four bearings are test bearings (the channel name gives the number)
        "sensor_location": "test_bearing",
        "sensor_mounting": "pedestal",
        "quantity": "acceleration",
        "axis": axis,
        "unit": "unknown",
        "fs": 20000,
    }


# Rexnord ZA-2115 (Qiu et al. 2006): 16 rollers per row of 0.331 in, pitch 2.815 in, 15.17 deg
ORDERS = fault_orders(16, 0.331, 2.815, 15.17)
CHANNELS = {
    **{f"bearing{b}_{a}": _ch(a) for b in (1, 2, 3, 4) for a in ("x", "y")},
    **{f"bearing{b}": _ch() for b in (1, 2, 3, 4)},
}
TESTS = {  # folder in the archive -> (run id, channels, failed bearings, failure)
    "1st_test": (
        "test1",
        [f"bearing{b}_{a}" for b in (1, 2, 3, 4) for a in ("x", "y")],
        "bearing_3+bearing_4",
        "bearing 3 inner race; bearing 4 roller element",
    ),
    "2nd_test": (
        "test2",
        [f"bearing{b}" for b in (1, 2, 3, 4)],
        "bearing_1",
        "bearing 1 outer race",
    ),
    # the files of the 3rd test sit in 3rd_test/4th_test/txt
    "3rd_test": (
        "test3",
        [f"bearing{b}" for b in (1, 2, 3, 4)],
        "bearing_3",
        "bearing 3 outer race",
    ),
}


def recordings(raw_dir):
    base = raw_dir / "4. Bearings" / "4. Bearings" / "IMS"  # zip -> 7z -> one rar per test
    for folder, (run, channels, failed, failure) in TESTS.items():
        files = sorted(
            p for p in (base / folder).rglob("*") if p.is_file() and p.name.count(".") == 5
        )
        times = [datetime.strptime(p.name, "%Y.%m.%d.%H.%M.%S") for p in files]
        start, end = times[0], times[-1]
        for path, t in zip(files, times, strict=True):
            table = pd.read_csv(path, sep="\t", header=None, engine="pyarrow", dtype="float64")
            yield {
                "recording_id": f"{run}_{path.name}",
                "native_label": "unknown",
                "fault_type": "unknown",
                "fault_location": "unknown",
                "speed_rpm": 2000.0,
                "load": 6000.0,
                "load_unit": "lbs",
                "bearing_model": "ZA-2115",
                "run_id": run,
                "time_s": (t - start).total_seconds(),
                "rul_s": (end - t).total_seconds(),
                "measured_at": t.isoformat(),
                "failed_bearing": failed,
                "failure": failure,
                **ORDERS,
                "signals": {ch: table[i].to_numpy() for i, ch in enumerate(channels)},
            }
