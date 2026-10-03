# Guide: bearing-datasets for newcomers

This guide explains the library from zero: what it is, the few concepts you need, recipes for
common tasks, notes on each dataset, and answers to frequent questions. You do not need to read
the source code. For a hands-on version, run [`examples/usage.ipynb`](../examples/usage.ipynb).

**Contents**

1. [What the library is (and is not)](#1-what-the-library-is-and-is-not)
2. [Concepts](#2-concepts)
3. [First steps](#3-first-steps)
4. [How it works](#4-how-it-works)
5. [Recipes](#5-recipes)
6. [Notes on each dataset](#6-notes-on-each-dataset)
7. [FAQ and troubleshooting](#7-faq-and-troubleshooting)
8. [Bearing vocabulary](#8-bearing-vocabulary)

---

## 1. What the library is (and is not)

**It is** a way to get public bearing-fault datasets (CWRU, Paderborn, HUST, Ottawa, ...)
and your own private ones in **one common format**:

* the data is downloaded from the original source, checked against known checksums, and
  converted once per datasets folder (which a team can share);
* every dataset becomes **one metadata table** (what each signal is) plus **the signals**;
* you read them with a few Python functions (or directly with pandas/polars).

**It is not** a machine-learning library. It does not define train/test splits, features or
models; those belong to each study. It gives you clean, well-described data to start from.

## 2. Concepts

| concept | meaning |
|---|---|
| **root** | the folder that holds the built datasets, e.g. `/data/bearing_datasets`. Everyone on a server can share one root. Save it once with `bearing-datasets root <folder>` (or `bd.set_root(folder)`); it is remembered for your user. |
| **dataset** | one published dataset, e.g. `cwru`. In code: `ds = bd.open("cwru")`. |
| **recording** | one acquisition: the machine ran in one state (its faults, speed and load) and one or more sensors were recorded **at the same time**. Identified by `recording_id`. |
| **channel** | a sensor (e.g. `DE` = drive-end accelerometer) or one axis of a sensor, named as the dataset names it. |
| **signal** | one channel of one recording, i.e. one 1-D array of samples. Identified by `signal_id` = `<recording_id>/<channel>`; `ds.signal(signal_id)` returns the samples as a numpy array. |
| **metadata** | the table describing all signals of a dataset, **one row per signal**. |

The most important metadata columns:

| column | meaning | example |
|---|---|---|
| `fault_type` | the fault(s) present in the **machine** | `normal`, `inner`, `inner+outer` |
| `fault_location` | the position of each faulty part | `motor_bearing_de`, `none` |
| `sensor_location` | the bearing or part the sensor of this signal measures | `motor_bearing_nde` |
| `sensor_at_fault` | whether this sensor is at a faulty position | `False` |
| `operating_condition` | the dataset's own name of the operating regime (speed, load) | `N15_M07_F04` |
| `fs` | sampling rate, in Hz | `12000` |
| `native_label` | the label exactly as the original dataset names it (to compare with papers) | `IR007_1` |
| `bearing_id` | the physical bearing that was tested; the same id means the same bearing | `KA04` |

Two special values appear in the table instead of empty cells:

* **`none`**: the value does not apply (e.g. `fault_location` of a healthy machine);
* **`unknown`**: the dataset does not say (e.g. the `unit` of some accelerometers).

`ds.columns()` gives the exact meaning of every column of a dataset.

## 3. First steps

```bash
# 1. install from PyPI (no need to clone the repository)
pip install bearing-datasets

# 2. tell the library where the datasets are (saved for your user; works on Windows too)
bearing-datasets root /data/bearing_datasets

# 3. check which datasets exist; the ones marked [built] are ready to use
bearing-datasets list

# 4. (only if a dataset is not built yet) download + convert the ones you need; this can
#    take a while. Nothing else is downloaded.
bearing-datasets build cwru hust
```

Then in Python:

```python
import bearing_datasets as bd

ds = bd.open("cwru")
meta = ds.metadata()                      # pandas DataFrame, one row per signal
x = ds.signal(meta.signal_id.iloc[0])   # numpy array
```

That is all you need to start. The rest of this guide is details.

## 4. How it works

```
BUILD (once per folder)                              READ (every day)

dataset.yaml  ── where to download from              bd.open("cwru")
     │                                                   │
     ▼                                                   ▼
<root>/_raw/   ── downloaded files (cached, checked)  ds.metadata()  ── reads metadata.parquet
     │                                                   │
     ▼                                                   ▼
builder.py    ── reads the raw files, one dict        ds.signal(id) ── reads one signal from
     │           per recording                                        signals/*.parquet
     ▼
<root>/cwru/metadata.parquet, signals/, manifest.json
```

**On disk**, each built dataset is a folder:

| file | content |
|---|---|
| `metadata.parquet` | the metadata table (open it with `pd.read_parquet`, no library needed) |
| `signals/part-<dtype>.parquet` | the samples: columns `signal_id` and `signal`, compressed |
| `manifest.json` | when/how it was built, sources used, checksums, citation, column descriptions |

Signals keep the **original dtype** of the data (e.g. `float64` for CWRU). There is one signal
file per dtype.

**The code**, in case you want to look (7 short files in `src/bearing_datasets/`):

| file | what it does |
|---|---|
| `dataset.py` | reading: `open`, `Dataset.metadata`, `Dataset.signal`, ... (start here) |
| `schema.py` | the list of columns, their descriptions, and the checks a build must pass |
| `build.py` | building: runs a dataset's builder and writes the files |
| `sources.py` | downloading: sources, mirrors, checksums, archives |
| `io.py` | small helpers to read `.mat` / `.csv` files |
| `cli.py` | the `bearing-datasets` command |
| `datasets/<name>/` | one folder per dataset: `dataset.yaml` (sources, citation, columns) and `builder.py` |

## 5. Recipes

### Filter the metadata

The metadata is a pandas DataFrame, so use normal pandas:

```python
meta = bd.open("cwru").metadata()
meta[(meta.fault_type == "inner") & (meta.fs == 12000)]
meta.query("sensor_location == 'motor_bearing_de' and load == 1")
meta.groupby("fault_type").size()
```

### One signal, with a time axis

```python
row = meta.iloc[0]
x = ds.signal(row.signal_id)
t = np.arange(len(x)) / row.fs          # seconds
part = ds.signal(row.signal_id, start=0, stop=int(row.fs))   # only the first second
```

### Signals in a chosen unit

```python
a = ds.signal(row.signal_id, unit="m/s^2")      # float64, converted from the stored unit
rec = ds.recording("12k_DE_IR007_1", unit="g")
df = ds.with_signals(meta, unit={"acceleration": "g", "speed": "Hz"})   # others as stored
```

Signals stored in volts are converted with the `sensitivity` column when the dataset gives it.
A signal in `unknown`, `counts` or `normalized` cannot be converted and raises `ValueError`:
filter on `meta.unit` first. See the README's [Units](../README.md#units) for the list.

### All channels recorded together

```python
channels = ds.recording("12k_DE_IR007_1")    # {"DE": array, "FE": array, "BA": array}
```

### Only sensors on the faulty bearing

`fault_type` describes the machine: every sensor of a faulty machine has the fault label,
even sensors far from the faulty bearing. `sensor_at_fault` says whether the sensor is at a
faulty position (its `sensor_location` is in `fault_location`, or one contains the other, like
`gearbox` and `gearbox_bearing_input`). Keep only those sensors, plus healthy machines:

```python
meta = meta[meta.sensor_at_fault | (meta.fault_type == "normal")]
```

This drops every faulty recording that has no sensor at the fault: datasets with only
electrical sensors (`motor_supply`, e.g. lenze_mb), and most unbalance and misalignment
faults, located at the rotor or the coupling where no sensor sits. Check what is left with
`meta.groupby(["dataset", "fault_type"]).size()`. Unknown positions are never at the fault.

### Signals in a DataFrame

```python
df = ds.with_signals()                                   # all rows, plus a "signal" column
df = ds.with_signals(meta[meta.fault_type == "inner"])   # only the rows you selected
df = ds.with_signals(meta.head(5), start=0, stop=4096)   # the first 4096 samples of each
```

`with_signals` keeps the rows, their order and their index, and adds one numpy array per row
(in the original dtype). Without the package, the same with pandas alone:

```python
ids = meta.loc[meta.fault_type == "inner", "signal_id"].tolist()
signals = pd.concat([pd.read_parquet(f, filters=[("signal_id", "in", ids)])
                     for f in ds.signal_files()])
df = meta.merge(signals, on="signal_id")
```

Everything you load must fit in memory. Paderborn, for example, needs more than 10 GB for all
channels; filter first.

### Process a big dataset without loading it all

```python
for signal_id, x in ds.iter_signals(meta.signal_id):
    features = compute_features(x)       # one signal in memory at a time
```

### Fixed-length windows

```python
window = 2048
X, y = [], []
for (sid, x), label in zip(ds.iter_signals(meta.signal_id), meta.fault_type):
    n = len(x) // window
    X.append(x[: n * window].reshape(n, window))
    y += [label] * n
X = np.concatenate(X)
```

### Train/test split without leakage

Windows from the same physical bearing look alike. Split **by bearing** (or at least by
recording), **before** windowing:

```python
from sklearn.model_selection import GroupShuffleSplit       # needs scikit-learn installed

splitter = GroupShuffleSplit(test_size=0.25, random_state=0)
train_idx, test_idx = next(splitter.split(meta, groups=meta.bearing_id))
train_meta, test_meta = meta.iloc[train_idx], meta.iloc[test_idx]
```

For datasets without `bearing_id`, group by `recording_id`. To test generalisation to new
operating conditions, group by `operating_condition` (or `load`, `speed_rpm`) instead.

### Bearing fault frequencies in Hz

Datasets with `bpfo`, `bpfi`, `bsf`, `ftf` give them in orders of the shaft speed (multiples
of the rotation frequency), so they hold at any speed. In Hz, for a recording at `speed_rpm`:

```python
meta["bpfo_hz"] = meta.bpfo * meta.speed_rpm / 60
```

`bsf` is the ball spin frequency; a rolling element defect mostly shows at 2 x `bsf` (it hits both
races on each turn). Some tables, like CWRU's, list 2 x BSF under "rolling element".

### Resample to a common sampling rate

```python
from fractions import Fraction
from scipy.signal import resample_poly

ratio = Fraction(12000, int(row.fs)).limit_denominator(1000)
x12k = resample_poly(x, ratio.numerator, ratio.denominator)
```

### Several datasets

```python
all_meta = bd.load_metadata(["cwru", "paderborn", "hust"])   # only the columns all have
datasets = {name: bd.open(name) for name in all_meta.dataset.unique()}
x = datasets[row.dataset].signal(row.signal_id)            # read through the right dataset
```

### A PyTorch dataset

PyTorch is not a dependency of this library; install it in your own environment.

```python
import torch

class Windows(torch.utils.data.Dataset):
    def __init__(self, ds, meta, window=2048, classes=None):
        self.ds, self.window = ds, window
        self.meta = meta.reset_index(drop=True)
        self.classes = classes or {c: i for i, c in enumerate(sorted(meta.fault_type.unique()))}

    def __len__(self):
        return len(self.meta)

    def __getitem__(self, i):
        row = self.meta.iloc[i]
        x = self.ds.signal(row.signal_id)
        start = np.random.randint(0, len(x) - self.window)     # a random window
        x = torch.tensor(x[start : start + self.window], dtype=torch.float32)
        return x, self.classes[row.fault_type]
```

`Dataset` objects work with several `DataLoader` workers.

### Store only part of a large dataset

Some datasets are big (BJTU bogie: ~32 GB built). If you only need some channels or
conditions, build a subset under its own name; the full download is still needed, but less
is stored:

```bash
# only the motor drive-end accelerometer, only healthy and motor-fault recordings
bearing-datasets build bjtu_bogie --channels CH1 CH2 CH3 \
    --where native_label=M0_G0_LA0_RA0,M1_G0_LA0_RA0,M2_G0_LA0_RA0 --as bjtu_motor
```

`--where` accepts any column of the recordings (`fault_type`, `load`, `speed_rpm`, `native_label`,
...) with a comma-separated list of values. In Python:
`bd.build("bjtu_bogie", channels=[...], where={"load": [0]}, as_name="bjtu_load0")`.
The selection is saved with the build: `bearing-datasets build bjtu_motor --force` rebuilds
the same subset.

To avoid the full download too, `--files` downloads only the raw files whose names match
(the names are in the dataset's `files.lock.json`). Include every part of a split archive:

```bash
bearing-datasets build paderborn_rtf --files "B01*" "B02*" "B03*" --as paderborn_rtf_small
```

### Free the space of the downloads

By default the downloaded raw files stay in `<root>/_raw/`, so a rebuild or another subset
does not download again. Once a dataset is built they are no longer needed to read it, and
they often take more space than the built dataset. Delete them with:

```bash
bearing-datasets clean-raw cwru paderborn --dry-run   # what would be deleted, and how much
bearing-datasets clean-raw cwru paderborn             # delete them
bearing-datasets clean-raw --all-built                # every dataset built in this folder
bearing-datasets build cwru --clean-raw               # build, then delete its downloads
```

In Python: `bd.clean_raw(["cwru"])`. Only the copies in `<root>/_raw/` are deleted: the files
of a private dataset (its `local` source) are never touched, and a raw file still used by
another built dataset is kept. Rebuilding a cleaned dataset downloads it again; for sources
that are slow or may disappear (a personal NAS, Google Drive quotas), consider keeping them.

### Cite

```python
print(bd.open("paderborn").cite())
```

Cite each dataset you use, and this library too (see [Citing](../README.md#citing)).

## 6. Notes on each dataset

`bearing-datasets info <name>` prints the full description, license and citation.

**cwru**: Case Western Reserve University.
* Seeded faults of 0.18-0.71 mm on the drive-end (DE) or fan-end (FE) bearing of the motor,
  loads 0-3 hp; `fault_severity` is the fault diameter (levels 1-4).
* Each `.mat` file is one recording with up to 3 accelerometers: `DE`, `FE` (on the motor
  casing at each end: `motor_bearing_de`, `motor_bearing_nde`) and `BA` (base plate).
* The normal (healthy) data exists **only at 48 kHz**, while many papers use the 12 kHz fault
  data: resample or decimate the normal data to 12 kHz.
* Normal recordings have no `BA` channel.
* `bearing_id`: each fault size at each end is its own seeded bearing (21 in total; the 3, 6
  and 12 o'clock outer race positions count as one), but all normal recordings come from one
  healthy bearing: grouped splits work for the fault classes, not for the healthy one (see
  [diversity](diversity.md)).
* `native_label` is the label of the website (e.g. `OR007@6_1`), and `source_file` is the file
  number papers cite (e.g. `130.mat`).

**hust**: Hanoi University of Science and Technology.
* One accelerometer, 51.2 kHz; 5 bearing models (6204-6208, in `bearing_model`); compound
  faults such as `inner+rolling_element`.
* The original files contain a variable called `fs` that is actually the shaft frequency;
  here it was converted to `speed_rpm`, and the real sampling rate (51.2 kHz) is in `fs`.

**hse_similar_system**: Esslingen University of Applied Sciences, extended similar-system set.
* Downloaded from Kaggle's public API: no Kaggle account needed.
* Four "bearing types" (NU204-E plastic cage on rig a and b, NU204-E metal cage, STO20
  needle): made for transfer between bearing types and rigs; split by `bearing_id`.
* `original_recording` > 0 selects the 300 recordings of the original set (IEEE Access 2025).

**hustbearing**: Huazhong University of Science and Technology (HUSTbearing), not to be
confused with `hust` (Hanoi).
* 9 health states (medium and severe faults, `fault_severity`) x 11 speeds; triaxial accelerometer
  `X`, `Y`, `Z` at 25.6 kHz.
* Speed is only known from the file name, in `operating_condition` (`20Hz` ... `80Hz`, or
  `0-40-0Hz` with `speed_profile=inc_dec`); there is no `speed_rpm` column.
* The raw files have a speed column that the authors call meaningless; it is not stored.

**mehran_uet**: Mehran UET induction motor.
* Fault recordings have 6 channels (triaxial vibration in g + 3 phase currents, recorded
  together); the healthy and broken-rotor-bar recordings have only vibration or only current.
* The accelerometer saturates at +-2.048 g in some fault recordings (mostly the y axis).

**ottawa_uored**: University of Ottawa (UORED-VAFCLS).
* 20 bearings, each recorded healthy, then with a developing fault, then fully faulty
  (`fault_severity`, levels 0-2).
* Channels: accelerometer, microphone and a temperature difference, all at 42 kHz.

**upm_citef**: Universidad Politecnica de Madrid (CITEF), three studies in one dataset (`study`).
* Very shallow milled defects (0.006-0.032 mm); depth per component in `depth_or_mm`,
  `depth_ir_mm`, `depth_re_mm`; `fault_severity` F1-F4 is only comparable within a study.
* `Rod_1` is on the faulty bearing's housing (`test_bearing`), `Rod_2` on the other one
  (`support_bearing`), `Rod_3` on the tightening tower (`rig`).

**vibrobox**: VibroBox, five records on one stand (`subset`) from constant to widely varying speed.
* Vibration is the raw integer wav output of a 32 mV/g sensor; `speed_setting` keeps the record's
  text (e.g. `650+5`, `0...900`). The varying-speed subsets have an irregular tachometer
  (`tach_speed` x 30 = rpm, times in `tach_time_unix`).

**urma_crti**: CRTI research unit, Annaba (Algeria).
* One accelerometer, 25.6 kHz, 10.24 s; speed set by the drive's supply frequency
  (`supply_hz`, 30-50 Hz).
* Labels come from French variable names; the combined fault's parts are not stated
  (`fault_type=bearing`).

**uoemd**: University of Ottawa electric motors (UOEMD-VAFCVS).
* 8 motors, one per state (healthy, faulty bearing and 6 other motor faults); the motor is
  confounded with the label, so a model can learn the motor instead of the fault.
* Speed in `operating_condition` (constant `15Hz`...`60Hz`, or ramps like `15-45Hz`, with
  `speed_profile`); `load_state` loaded/unloaded.

**susu**: South Ural State University, sensor rotating with the shaft.
* 5 bearings at 20 Hz (paper) and 18 Hz (extra, undocumented set).
* The 3 channels hold linear and angular acceleration in an undocumented order (`ch1`-`ch3`).
* No license stated in the repository: cite the paper.

**sqv**: SpectraQuest runs from standstill to 3000 rpm and back (`speed_profile=inc_dec`),
speed knob turned by hand, so every run has its own speed curve: use the `speed_pulse`
channel to track it. Recordings last 1.5 to 30 s.

**paderborn**: Paderborn University (KAt).
* 32 bearings (6 healthy, 12 with artificial damage, 14 with real damage), 4 operating
  conditions, 20 repetitions each.
* 7 channels at 3 different sampling rates (64 kHz, 4 kHz, 1 Hz): always read `fs` from the
  row of the signal.
* One file of the official archive (`N15_M01_F10_KA08_2`) is cut off and zero-filled at the
  end; it is recovered from its intact part, but its vibration is 2.98 s long instead of 4 s.
* License CC BY-NC (non-commercial).

**kaist_load**: KAIST rotating machine under 0/2/4 Nm.
* Bearing faults (housing A: `test_bearing`; housing B: `support_bearing`), shaft
  misalignment and rotor unbalance, 3010 rpm.
* Vibration, temperature + motor current, and acoustic were recorded by different systems,
  so each state has up to 3 recordings (`..._vibration`, `..._current_temperature`,
  `..._acoustic`); group them by `native_label`. Channels have 3 sampling rates.
* Acoustic exists only for normal and 0.3 / 1.0 mm bearing faults at 0 Nm; phases V and W
  are missing in the outer race current files.
* Vibration unit left `unknown`: the paper says g, the file export says SI.

**kaist_speed**: KAIST, same test bed as `kaist_load`, speed varying randomly 680-2460 rpm.
* Vibration (25.6 kHz), motor current (100 kHz) and speed are separate recordings of the
  same run: group them by `native_label` + `trial`. Housing A is `test_bearing_de`, housing B
  `test_bearing_nde` (the faulty bearing is in B, except the constant-speed ball fault).
* The speed is irregularly sampled: its `fs` is only the mean rate; use the `speed_time_s`
  channel for the exact time of each sample.
* `trial=constant`: one extra 600 s vibration recording per state at 3010 rpm.

**cumtb_pitch**: CUMTB scaled wind turbine pitch bearing, very low speed (1-3 rpm) and heavy,
time-varying load.
* Each 10 min acquisition is stored as ~24 chunks of ~26 s (`chunk`): chunks of one state
  come from one acquisition, so split by state, not by chunk.
* `ITRC` is a crack at the root of the inner ring's gear teeth (`fault_type=gear`).

**dcase_bearing**: DCASE 2022 Task 2 bearing, microphone only, made for unsupervised anomalous
sound detection under domain shift.
* `dcase_split` keeps the challenge split (train has only normal clips) so results can be
  compared with the literature; `section` / `domain` give the domain shift.
* Anomalies are a damaged machine (eccentricity), labelled `fault_type=other`.

**dirg**: Politecnico di Torino, high-speed aeronautical roller bearings.
* `session=stationary`: 7 bearings (healthy, 3 inner ring and 3 roller indentations) at up to
  17 speed/load cases, 51.2 kHz; `session=endurance`: bearing 4A monitored for ~230 h,
  102.4 kHz (read `fs` per row). The endurance files are ordered by `acquisition`.
* `load` is computed from the load cell voltage, so it scatters around 1000/1400/1800 N.

**lenze_mb**: Lenze, bearing faults seen only through the drive's own signals.
* No accelerometer: phase currents/voltages, DC bus, encoder angle and speed logged by the
  inverter at 16 kHz. Some channels are in internal inverter units (see `unit`).
* 5 pitting levels + one heavy artificial damage (`fault_severity`, levels 1-6), 16 operating
  conditions each.
* License CC BY-NC (non-commercial).

**mcc5_thu_gearbox**: Tsinghua / MCC5 gearbox under time-varying speed or load.
* Bearing faults only appear together with a broken tooth (`gear+inner`, `gear+outer`).
* `speed_profile` says whether the speed cycles (`varying`) or the load does (`constant`);
  `speed_rpm` (the set speed) / `load` hold the constant value or the peak of the cycle. The `speed`
  channel is a key-phase pulse signal.

**hit_intershaft**: Harbin Institute of Technology, inter-shaft bearing inside a dual-rotor
aero-engine.
* The authors already cut the signals into 20480-sample segments (0.82 s): each is a
  recording. Segments of the same test and speed pair come from the same acquisition, so
  split by `bearing_id` (one test per file) or at least by speed pair to avoid leakage.
* Two speeds per recording: `lp_rpm` and `hp_rpm`.

**saarland**: Saarland University (ZeMA), designed for domain shift.
* Each of the 3 bearings (`bearing_id`) is measured undamaged and damaged under a full grid of
  speed, load level (`force_level`), mounting position, run and worker: use leave-one-group-out
  splits (by bearing, position or run).
* Metadata comes from the dataset's `info.csv`; files at undocumented speeds and misfiled copies
  in the archive are not used.

**sdust**: Shandong University of Science and Technology, bearing subset only.
* 10 states x constant (`1000rpm` ...) and randomly varying (`1000-2000rpm` ...) speeds x 4
  loads, in `operating_condition` / `speed_profile` / `load`.
* The two triaxial sensors are named as in the files (`upper`, `lower`); which one sits on the
  bearing housing is not documented (`sensor_location=unknown`).

**nln_emp**: Royal Netherlands Navy, two industrial motor-pump sets.
* Bearing faults are one group among many faults (`native_label` keeps the folder name, e.g.
  `bearing bpfo 2`, `align angular 3`); `setup` motor_2 has the bearing faults.
* Vibration (12 s) and electric (15 s) samples come from separate systems: `measurement`
  says which. Several samples per test (`repetition`), so split by test, not by sample.
* Four folders are empty in the published archive (listed in `bearing-datasets info nln_emp`).

**bjtu_bogie**: Beijing Jiaotong University, subway bogie test rig.
* Faults of the motor (electrical, bearing, bowed shaft), gearbox (gear teeth and bearing) and
  left/right axle box bearings, single and compound: 51 health states x 9 working conditions.
* 24 channels at 64 kHz: `sensor_location` is `motor_bearing_de` / `_nde`,
  `gearbox_bearing_input` / `_output`, `axle_bearing_left` / `_right`, `motor_supply`
  (currents), `motor_shaft` (speed) or `ambient` (microphones). Channel names are the
  dataset's (`CH1`...`CH24`).
* Compound faults list every fault: `fault_type = "electrical+inner"` with
  `fault_location = "motor_stator+gearbox_bearing"` (same order); `fault_detail` says it in
  words.
* The accelerometer axes are not documented: `axis` x/y/z is only the channel order.
* Large: 30 GB download, ~32 GB built. Consider a subset (see
  [Recipes](#store-only-part-of-a-large-dataset)).

**jnu**: Jiangnan University. 12 recordings, one vertical accelerometer at 50 kHz, faults on
the inner race, outer race and roller at 600/800/1000 rpm. Normal recordings are 3x longer,
and the amplitude is clipped at different ranges in different files.

**mfpt**: MFPT Society test rig plus 3 real-world recordings (`field_data`). Two sampling rates
(97,656 Hz for baseline and the first outer race files, 48,828 Hz for the variable-load
ones). The failed element of the real-world recordings is not documented (`fault_type =
bearing`).

**ottawa_2018**: University of Ottawa, **time-varying speed**. There is no constant `speed_rpm`;
`speed_profile` says how the speed changes, and the `encoder` channel (1024 pulses per
revolution) gives the instantaneous speed. 200 kHz.

**seu**: Southeast University drivetrain simulator: a bearing subset and a gear subset
(`subset`), 8 channels. The sampling rate (5120 Hz) is inferred, the files are truncated,
and the location of the fault inside the gearbox is not documented (`fault_location =
gearbox`).

**sca**: real machines of a pulp and paper mill, measured daily for months. One recording is
one measurement at one sensor position; the label can change over time (normal, then the
fault). Measurements with the machine off have `fault_type = unknown` and
`machine_running = False`. `source_file` keeps the dataset's own train/test files, and each
position has its own bearing fault frequencies (`bpfo`, `bpfi`, `bsf`, `ftf` columns).

**mafaulda**: machinery fault simulator with unbalance, horizontal/vertical misalignment and
bearing faults (alone or with unbalance), 49 speeds; 8 channels incl. a tachometer and a
microphone. Large (12.9 GB download).

**phm09**: PHM 2009 gearbox challenge, labeled set: 14 cases with gear, bearing and shaft
faults, often combined (e.g. `fault_type = gear+gear+rolling_element`, with the part and
shaft of each fault in `fault_location`, e.g. `gearbox_gear_input`), 5 speeds x 2 loads x 2
repeats.

**Run-to-failure datasets (`ims`, `femto`, `xjtu_sy`, `kaist_rtf`, `unsw`, `wt_hss`, `ferrara_rtf`,
`paderborn_rtf`, `dlr_needle`)**: a bearing runs until it fails and is
recorded periodically. Each run has a `run_id`; each snapshot has `time_s` (since the start)
and `rul_s` (remaining useful life, end of life = last snapshot). The fault of each
snapshot is `unknown`; what failed at the end is in `failure` / `failed_bearing`. Split by
`run_id`.
* **ims**: 3 tests, 4 bearings on one shaft (test 1 has x/y channels per bearing).
* **femto**: 17 runs (6 learning + 11 test, complete); `official_set` marks the snapshots
  of the truncated official test set. Temperature is stored as separate recordings.
* **xjtu_sy**: 15 runs, 3 operating conditions, horizontal/vertical accelerometers.
* **kaist_rtf**: 1 run of 128 h, one 78 s snapshot per hour (x/y vibration + 2
  temperatures); the failed element is not stated. The raw files contain short NaN gaps,
  kept as published: use `np.nanmean` or drop NaNs before processing.
* **unsw**: 4 tests; progress is in shaft revolutions (`shaft_cycles`, `rul_cycles`), not
  seconds. Most measurements are at 6 Hz; some occasions add 12, 15 and 20 Hz (`speed_rpm`). All
  channels are in V (sensitivities in `bearing-datasets info unsw`).
* **wt_hss**: field data from a wind turbine, one 6 s snapshot per day for 50 days.
  `tach_times_s` holds tachometer pulse *times*, not samples. License CC BY-NC-SA.
* **ferrara_rtf**: 6 tests at 4 loads; every bearing ended with an outer raceway defect.
  `time_s` is nominal (5 min between snapshots, 1 h for the first 453 of E4).
* **paderborn_rtf**: 17 tests, 1.6 s every ~12 s, 128 kHz (B01-B09) or 64 kHz (B10-B17);
  speed and loads change at random between recordings (`speed_rpm`, `load`,
  `dynamic_load_peak_n` per row). 152 GB: build a subset with `--files`, e.g.
  `--files "B01*" "B02*" "B03*" --as paderborn_rtf_small` (3 GB).
* **dlr_needle**: oscillating (not rotating) needle bearings, two per test; 11 channels at 4
  sampling rates. 36.7 GB: e.g. `--files "Test_4.zip" "Test_6.zip" "Test_7.zip" "Test_8.zip"`
  (1.9 GB); Test 3 is split in five zips, which must all be included.

**my_cwru** (private-dataset example): not part of the package; its definition lives in
`examples/private_datasets/my_cwru/` and shows how to build your own data from a local folder
(`local` source). It reads four CWRU files (normal, inner, ball, outer at 0 hp) that you
download into `~/data/my_cwru`. Built by path the first time:
`bearing-datasets build examples/private_datasets/my_cwru`; after that it is known by name:
`bd.open("my_cwru")`, `bearing-datasets info my_cwru`.

## 7. FAQ and troubleshooting

**`ValueError: no datasets folder`**
: Save the folder once: `bearing-datasets root /data/bearing_datasets` (or
  `bd.set_root(...)` in Python), or pass `bd.open("cwru", root="...")`.

**Where is the datasets folder saved? How do I use another one?**
: In a small settings file: `%APPDATA%\bearing_datasets\config.json` on Windows,
  `~/.config/bearing_datasets/config.json` on Linux and macOS. `bearing-datasets root` shows
  the folder in use and where it comes from. To use another folder once, pass `--root` /
  `root=...`; the environment variable `BEARING_DATASETS_ROOT`, when set, overrides the saved
  folder.

**`bearing-datasets` is not recognized / command not found**
: The package was installed in a project environment (`uv add`), whose `.venv` is not on
  PATH. Use `uv run bearing-datasets ...` from the project folder, or activate the environment
  (`.venv\Scripts\activate` on Windows), or install the command globally with
  `uv tool install bearing-datasets`
  and `uv tool update-shell`.

**`KeyError` when reading a signal**
: `ds.signal()` takes a signal id, `'<recording_id>/<channel>'` (e.g. `'48k_Normal_0/DE'`);
  for all channels of a recording use `ds.recording('48k_Normal_0')`. The error message
  suggests the closest ids.

**A download stopped with "incomplete download"**
: Run the same command again: finished files are reused and a partial file resumes where it
  stopped.

**`FileNotFoundError: cwru is not built`**
: The dataset has not been converted in this root yet. Run
  `bearing-datasets build cwru` (or ask whoever manages the server).

**Why does a fan-end sensor say `fault_type = inner`?**
: `fault_type` describes the machine. `sensor_at_fault` says whether the sensor is at the
  faulty bearing (see [Recipes](#only-sensors-on-the-faulty-bearing)).

**I built a dataset with version 0.1 and the column names changed.**
: 0.2.0 renamed `condition` to `fault_type` (and its value `ball` to `rolling_element`), `rpm`
  to `speed_rpm` and `severity` to `fault_severity`. Datasets built with 0.1 are read with the
  new names (with a warning); rebuild them (`bearing-datasets build <name> --force`, no new
  download if the raw files are still cached) to get the standard locations,
  `sensor_at_fault`, `sensor_mounting` and the severity levels.

**Why did some columns disappear with `load_metadata`?**
: It keeps only the columns that every selected dataset has, so there are no missing values.
  Use `pd.concat([bd.open(n).metadata() for n in names])` to keep them all.

**What do `none` and `unknown` mean?**
: `none` = does not apply; `unknown` = the dataset does not say. The tables never have empty
  cells.

**My program runs out of memory.**
: Do not load all signals at once: filter the metadata first, read with `filters=`, or loop
  with `ds.iter_signals()`.

**`polars` fails when concatenating the signal files.**
: A dataset whose channels have different dtypes has one file per dtype, and a polars list
  column has a single dtype. Read one file at a time, or cast before `pl.concat`.

**The download failed / is very slow.**
: Run the same `build` command again: downloads resume where they stopped, and files already
  downloaded are reused from `<root>/_raw/`. If the official server is down, the other
  sources listed in the dataset's `dataset.yaml` are tried automatically.

**The upstream dataset changed, or a builder was fixed. How do I update?**
: `bearing-datasets build <name> --force` rebuilds it (without downloading again).

**Are the signals exactly the original data?**
: Yes: the samples are copied bit for bit, in their original dtype. `bearing-datasets verify
  <name>` checks the stored signals against the checksum recorded at build time.

**How do I add a dataset (public or from my lab)?**
: See [CONTRIBUTING.md](../CONTRIBUTING.md): one `dataset.yaml` and one short `builder.py`.

**Can I add an internal dataset without publishing it?**
: Yes. Keep its folder (`dataset.yaml`, `builder.py`) outside this repository and build it
  with `bearing-datasets build /path/to/folder`; see
  [Private datasets](../CONTRIBUTING.md#private-datasets). No change to this repository is
  needed. After the first build, it is known by name in that root folder (`bd.open("my_rig")`,
  `bearing-datasets build my_rig`), because the build records where its definition lives.

## 8. Bearing vocabulary

| term | meaning |
|---|---|
| inner race / outer race | the inner and outer rings of a rolling bearing (ISO 5593: inner ring, outer ring); faults there are `inner` / `outer` |
| rolling element | the balls, rollers or needles between the rings; faults there are `rolling_element` |
| cage | the part that keeps the rolling elements spaced; faults there are `cage` |
| drive end (DE) / non-drive end (NDE) | the two ends of a motor (IEC 60034-7): the end with the shaft extension (coupling side) and the opposite end, also called fan end (FE); in locations, `_de` / `_nde` |
| test bearing / support bearing | on a test rig, the bearing under study (seeded fault, swapped or run to failure) and the rig's own bearings that hold the shaft |
| pedestal / casing | a stand-alone bearing housing (pillow block), or the machine casing that holds the bearing, like a motor end shield (ISO 20816-1, "pedestal" and "housing-type" bearings); in `sensor_mounting` |
| seeded / artificial fault | a fault made on purpose (EDM, drilling, engraving) — `fault_origin = artificial` |
| real fault | a fault that grew during operation (e.g. accelerated lifetime test) — `fault_origin = real` |
| BPFO / BPFI / BSF / FTF | characteristic fault frequencies of the outer race, inner race, ball and cage, usually given in **orders** (multiples of the shaft frequency) |
| order | frequency divided by the shaft frequency (`speed_rpm / 60`); makes different speeds comparable |
| envelope spectrum | spectrum of the signal's amplitude; bearing faults show peaks at their fault frequency |
| run-to-failure | an experiment where a bearing runs until it fails, recorded periodically |

The location and mounting words follow ISO 20816-1 (measurement positions on bearing
housings), ISO 13373-1 (transducer location and orientation), IEC 60034-7 (D-end, N-end),
ISO 14224 (equipment units and maintainable items) and ISO 5593 (rolling bearing parts).
