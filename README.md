# bearing-datasets

[![PyPI](https://img.shields.io/pypi/v/bearing-datasets?cacheSeconds=3600)](https://pypi.org/project/bearing-datasets/)
[![Python](https://img.shields.io/badge/python-%E2%89%A5%203.10-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#license)
[![Datasets](https://img.shields.io/badge/datasets-69-orange)](#datasets)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23062167.svg)](https://doi.org/10.5281/zenodo.23062167)

**69 public bearing and rotating-machinery fault datasets in one common format**, downloaded
from their original sources. Every dataset becomes one metadata table (one row per signal) plus the
signals themselves, ready for pandas, polars, NumPy or PyTorch.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/VictorBauler/BearingDatasets/main/docs/assets/banner-dark.png">
  <img alt="100 ms of raw vibration from four datasets (cwru, jnu, dlr, hit_sm), sampled at 12 to 51.2 kHz, each labeled with the same metadata columns (fault_type=inner, rolling_element, outer)" src="https://raw.githubusercontent.com/VictorBauler/BearingDatasets/main/docs/assets/banner-light.png">
</picture>

Why:

* **Reproducible**: data comes from the official sources (with mirrors as fallback) and is
  checked against pinned checksums; the build records what was used.
* **Same format for every dataset**: the same column names and labels, so code written for one
  dataset works on the others.
* **Build once**: each dataset is built once into a folder you choose (on your laptop or on a
  server), then read from there. A team can point everyone to the same folder.
* **Fast and light**: compressed Parquet files; read one signal without loading the rest.

> **Important: code only, no data.** Each dataset is downloaded by you from its original
> source and **keeps its own license**, set by its authors. Confirm the license of every
> dataset before you use it: see [License](#license).

New here? Read the [guide](docs/guide.md) (concepts, recipes, FAQ) and run the notebook
[`examples/usage.ipynb`](examples/usage.ipynb). Have a dataset that is not listed?
[Add it](#add-your-dataset). Using it in a paper? Please [cite it](#citing).

**Contents**

* [Quick start](#quick-start): install, choose a folder, build, read
* [Datasets](#datasets): the list of datasets, what they contain and their size
* [Concepts in one minute](#concepts-in-one-minute): recordings, channels, signals, metadata
* [API](#api): Python functions and command line
* [The metadata table](#the-metadata-table): the columns and their values
* [On disk](#on-disk): the files of a built dataset
* [Documentation](#documentation): guide, notebook, contributing
* [Add your dataset](#add-your-dataset) · [Development with AI](#development-with-ai) ·
  [Citing](#citing) · [License](#license)

## Quick start

**1. Install** the package from PyPI (no need to clone the repository):

```bash
pip install bearing-datasets
# or, in a uv project:
uv add bearing-datasets
```

Add the `polars` extra (`pip install "bearing-datasets[polars]"`) to get the metadata as a
polars DataFrame. The latest development version installs from GitHub:
`pip install "bearing-datasets @ git+https://github.com/VictorBauler/BearingDatasets"`.

> **Command not found?** (common on Windows, e.g. "bearing-datasets is not recognized")
> `uv add` installs the command inside the project's `.venv`, which is not on your PATH.
> Run it through uv from the project folder, `uv run bearing-datasets list`, or activate the
> environment first (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate`
> elsewhere). To have the command everywhere, install it as a tool instead:
> `uv tool install bearing-datasets`
> then `uv tool update-shell` and open a new terminal. The examples below write
> `bearing-datasets ...`; prefix them with `uv run` if needed.

Clone the repository only to change the code or add a dataset (see
[CONTRIBUTING.md](CONTRIBUTING.md)); there, `uv sync` installs everything, including the
notebook and test tools.

**2. Choose the datasets folder** (any folder; a team can share one on a server). This is
saved for your user, so you only do it once, on Linux, macOS or Windows:

```bash
bearing-datasets root /data/bearing_datasets     # Windows: bearing-datasets root D:\datasets
bearing-datasets root                               # shows the current folder
```

The same from Python: `bd.set_root("/data/bearing_datasets")`. A different folder can still
be used for one command (`--root`) or one call (`root=...`), and the environment variable
`BEARING_DATASETS_ROOT`, when set, takes priority over the saved folder.

**3. Download the datasets you need.** Check which ones are already there: datasets marked
`[built]` are ready to use.

```bash
bearing-datasets list
```

Nothing is downloaded until you ask for it. Build (download + convert) only the datasets that
are missing; this is done once per folder (and anyone sharing the folder can use them):

```bash
bearing-datasets build cwru                 # one dataset
bearing-datasets build cwru hust paderborn  # several; resumable, downloads cached in <root>/_raw/
```

For large datasets you can store only a part (the download is the same, the disk used is
smaller). A subset gets its own name, so it never replaces the full dataset:

```bash
bearing-datasets build bjtu_bogie --channels CH1 CH2 CH3 --where load=0 --as bjtu_motor_de
```

**4. Use them in Python:**

```python
import bearing_datasets as bd

ds = bd.open("cwru")                         # fails with a hint if cwru is not built yet
meta = ds.metadata()                         # pandas DataFrame, one row per signal
inner = meta[(meta.fault_type == "inner") & (meta.fs == 12000)]

x = ds.signal(inner.signal_id.iloc[0])     # one signal, as a numpy array
a = ds.signal(inner.signal_id.iloc[0], unit="m/s^2")  # the same, converted from g
df = ds.with_signals(inner)                  # the same rows + a "signal" column
```

## Datasets

**69 datasets** in 4 groups: bearing test rigs (37), machines with several fault types (22),
run-to-failure (9), field data (1).
How many distinct physical bearings each one has (for leave-bearing-out evaluation):
[docs/diversity.md](docs/diversity.md).

### Bearing test rigs (37)

Seeded or natural bearing faults on laboratory rigs.

| name | dataset | recordings | signals | download | on disk |
|---|---|---|---|---|---|
| `adelaide` | Univ. Adelaide: outer race defects of 5 edge slopes and 2 lengths; acceleration, displacement, load, sound | 159 | 1272 | 4.3 GB | 1.8 GB |
| `cumtb_pitch` | CUMTB: scaled wind turbine pitch bearing at 1-3 rpm, 11 faults (crack/spalling/wear) x 3 time-varying loads; vibration + acoustic | 1731 | 8655 | 11.7 GB | 4.6 GB |
| `cwru` | Case Western Reserve University: seeded bearing faults, DE/FE/base accelerometers | 161 | 411 | 0.7 GB | 0.16 GB |
| `dcase_bearing` | DCASE 2022 Task 2 bearing (MIMII DG): acoustic anomaly detection under domain shift (speed, mic position, factory noise) | 3599 | 3599 | 0.77 GB | 0.67 GB |
| `dirg` | Politecnico di Torino: aero roller bearings up to 30000 rpm + 230 h endurance test | 185 | 1110 | 3.2 GB | 2.7 GB |
| `dlr` | German Aerospace Center: aerospace axial ball bearings, inner/outer spalls of 3 widths | 28 | 28 | 0.16 GB | 0.08 GB |
| `ferrara_or` | Univ. Ferrara: outer ring EDM defects of 3 widths, each on 3 bearings; 2 loads x 3 speeds; no healthy | 54 | 54 | 0.13 GB | 0.11 GB |
| `fstf` | FSTF (Fez): smartphone sound of SKF 6004 bearings, single/combined faults and looseness, with and without stethoscope | 36 | 36 | 0.08 GB | 0.05 GB |
| `haust_ldv` | Henan Univ. of Sci. & Tech.: laser Doppler (non-contact) velocity, inner/outer/roller pitting x 3 sizes, 2 loads | 20 | 40 | 1.12 GB | 0.38 GB |
| `hit_intershaft` | HIT: inter-shaft bearing of a real aero-engine, 28 LP/HP speed pairs, rotor + casing sensors | 2412 | 14472 | 2.9 GB | 1.7 GB |
| `hit_sm` | HIT-SM: SpectraQuest + self-built rig, inner/outer faults of 3 sizes, 3 speeds | 42 | 42 | 0.07 GB | 0.03 GB |
| `hse_similar_system` | Esslingen Univ. (HSE): 4 bearing types (cylindrical, needle) on 2 rigs, for transfer learning | 600 | 600 | 0.60 GB | 0.02 GB |
| `hust` | HUST (Hanoi): 5 bearing types, single and compound faults | 99 | 99 | 0.7 GB | 0.3 GB |
| `hustbearing` | HUSTbearing (Huazhong): 9 health states, 10 constant speeds + 1 varying, triaxial | 99 | 297 | 1.2 GB | 0.28 GB |
| `jnu` | Jiangnan University: inner/outer/roller faults, 3 speeds | 12 | 12 | 0.08 GB | 0.02 GB |
| `just_slewing` | JUST: slewing bearing at 2-12 rpm, inner/outer/ball faults x 3 loads; 6 accelerometers + acoustic, 50 kHz | 180 | 1260 | 14.5 GB | 4.4 GB |
| `kaist_speed` | KAIST: inner/outer/ball faults under random varying speed; vibration, current, speed | 88 | 268 | 21.4 GB | 13 GB |
| `mehran_uet` | Mehran UET: induction motor, inner/outer faults of 6 sizes x 3 loads; triaxial vibration + 3-phase current | 41 | 231 | 0.33 GB | 0.03 GB |
| `mfpt` | MFPT Society: test rig + 3 real-world bearings | 23 | 23 | 0.06 GB | 0.03 GB |
| `neepu` | NEEPU: single and compound inner/outer/ball faults, 4 loads | 28 | 28 | 0.15 GB | 0.03 GB |
| `ottawa_2018` | Univ. Ottawa: time-varying speed, accelerometer + encoder | 60 | 120 | 0.8 GB | 0.27 GB |
| `ottawa_uored` | Univ. Ottawa UORED-VAFCLS: healthy → developing → faulty | 60 | 180 | 0.3 GB | 0.11 GB |
| `paderborn` | Paderborn University: artificial and real damage, vibration + motor currents | 2560 | 17920 | 5.4 GB | 4.2 GB |
| `saarland` | Saarland Univ.: 3 cylindrical roller bearings undamaged/damaged under a designed grid of speed, load, mounting position; triaxial | 1151 | 3453 | 38.8 GB | 8.7 GB |
| `sdust` | Shandong Univ. of Sci. & Tech.: 10 bearing states, 7 constant + 3 varying speeds, 4 loads, 2 triaxial sensors | 381 | 2286 | 19.2 GB | 2.6 GB |
| `sqv` | SpectraQuest run-up/run-down 0-3000 rpm, inner/outer faults at 3 levels, with speed pulses | 52 | 104 | 1.97 GB | 0.34 GB |
| `subf_v1` | SUBF v1: inner/outer race faults, wireless triaxial accelerometer, 6 h per class in 10 s segments (CC BY-NC-SA) | 6480 | 19440 | 1.71 GB | 0.23 GB |
| `subf_v2` | SUBF v2: inner/outer race faults, microphone, 6 h per class in 10 s segments (CC BY-NC-SA) | 6480 | 6480 | 0.66 GB | 0.26 GB |
| `susu` | South Ural State Univ.: wireless accelerometer mounted on the rotating shaft | 10 | 30 | 0.29 GB | 0.34 GB |
| `tecnalia_bearing` | Tecnalia MFS: healthy vs outer race, constant 50 Hz and speed ramps, 16 channels | 4 | 64 | 0.16 GB | 0.03 GB |
| `uc204` | UFPB: UC204 insert bearing, outer race grooves of 4 lengths x 3 loads, low-cost MEMS accelerometer | 150 | 150 | 0.06 GB | 0.01 GB |
| `uestc` | UESTC: UCPH 20 bearings, ball/inner/outer faults, 4 speeds, no load | 16 | 16 | 0.15 GB | 0.09 GB |
| `upm_citef` | UPM CITEF railway axlebox rig: spherical roller bearings, 3 studies (RE, OR+RE, OR/IR/RE defects) | 105 | 315 | 3.5 GB | 4.5 GB |
| `urma_crti` | CRTI Algeria: healthy, inner, outer, ball, combined; 5 supply frequencies | 23 | 23 | 0.05 GB | 0.04 GB |
| `vibrobox` | VibroBox: 6213 bearing normal/outer fault at constant, ramped and widely varying speed (0-975 rpm), 96 kHz, with tachometer | 319 | 565 | 2.2 GB | 2.0 GB |
| `vit_sq` | VIT Vellore SpectraQuest: ball bearing single and combined faults, 4 speeds, 3 added masses; triaxial | 50 | 150 | 0.33 GB | 0.19 GB |
| `vit_taper` | VIT Vellore: tapered roller bearing, roller/inner/wear/cage faults, 4 speeds x 2 trials; triaxial | 40 | 128 | 0.30 GB | 0.10 GB |

### Machines with several fault types (22)

Motors, gearboxes, pumps and bogies; bearing faults among others.

| name | dataset | recordings | signals | download | on disk |
|---|---|---|---|---|---|
| `arkansas` | Univ. Arkansas SpectraQuest: 38 single/double bearing and bent-shaft faults x 3 speeds x 25 trials; 8 accelerometers | 2925 | 26325 | 14.8 GB | 3.0 GB |
| `army_pla` | Army Eng. Univ. of PLA: bearing, gearbox and mixed bearing+gear faults; 3 speeds + speed sweep; triaxial | 64 | 192 | 1.19 GB | 0.33 GB |
| `bjtu_bogie` | BJTU-RAO bogie: motor, gearbox and axle box faults, 24 channels | 459 | 11016 | 30.4 GB | 22.8 GB |
| `estogu` | ESTU induction motor: bearing ball/ring, broken bars, winding short; inverter (11 frequencies) and grid, 6 loads; vibration, current, voltage | 432 | 3024 | 14.2 GB | 3.0 GB |
| `hust_transmission` | HUST transmission chain: motor, bearing, shaft, housing, pulley, gear faults and compounds; 6 speeds + run-up; 4 sensors | 98 | 392 | 1.7 GB | 0.37 GB |
| `im_vacd` | IM-VACD: 8 induction motor states (bearing, rotor, stator, supply), smartphone sound + accelerometer | 256 | 1024 | 3.68 GB | 0.24 GB |
| `isac` | ISAC Lab (Univ. Guilan): outer race and ball faults in 3 bearing positions, unbalance on 6 disks; 12 channels | 35 | 420 | 0.50 GB | 0.18 GB |
| `kaist_load` | KAIST: bearing faults, misalignment, unbalance, 3 loads; vibration, current, temperature, acoustic | 95 | 392 | 4.3 GB | 1.6 GB |
| `kimm_pmsm` | KIMM PMSM: bearing, magnet, stator, eccentricity faults; 4 sensor positions, physical disturbances | 450 | 1800 | 0.27 GB | 0.23 GB |
| `laspi` | LASPI gearbox: bearing, gear and combined faults, 3 speeds x 4 loads; motor current, voltage, vibration | 336 | 2352 | 2.0 GB | 2.1 GB |
| `lenze_mb` | Lenze-MB: inner ring pitting seen only through inverter signals (current, voltage, speed); CC BY-NC | 112 | 1232 | 3.2 GB | 2.2 GB |
| `mafaulda` | UFRJ machinery fault simulator: unbalance, misalignment, bearing faults | 1951 | 15608 | 12.9 GB | 13.0 GB |
| `mcc5_thu_gearbox` | MCC5-THU gearbox: gear faults + gear/bearing compound faults, time-varying speed and load | 240 | 1920 | 6.9 GB | 5.0 GB |
| `mcc5_thu_motor` | MCC5-THU motor: bearing, rotor, stator, supply faults and compounds; time-varying speed/load; vibration, current, torque | 282 | 2256 | 9.2 GB | 8.5 GB |
| `nln_emp` | Royal Netherlands Navy pump sets: motor/pump bearing faults + ~10 other faults; vibration, current, voltage | 3204 | 16913 | 20.8 GB | 22 GB |
| `phm09` | PHM 2009 challenge gearbox: gear, bearing and shaft faults (labeled) | 280 | 840 | 0.53 GB | 0.25 GB |
| `seu` | Southeast University: gearbox with bearing and gear faults, 8 channels | 20 | 160 | 1.6 GB | 0.37 GB |
| `tecnalia_gearbox` | Tecnalia gearbox: gear, bearing outer race and combined faults under stationary/variable speed/load; 16 channels | 14 | 224 | 0.57 GB | 0.19 GB |
| `uaq_upc` | UAQ/UPC: motor-gearbox-generator, bearing, rotor bar, unbalance, misalignment, gear wear; currents, vibration, temperatures, speed; stationary and start-up tests | 216 | 1728 | 40.6 GB | 5.4 GB |
| `uoemd` | Univ. Ottawa UOEMD-VAFCVS: 8 motors (bearing + 6 motor faults), constant and variable speed | 128 | 640 | 0.6 GB | 0.36 GB |
| `uos` | Univ. of Seoul: 3 bearing types (ball, cylindrical, tapered) x bearing faults combined with misalignment/unbalance/looseness; 6 speeds, 2 rates | 1152 | 1152 | 22.4 GB | 4.7 GB |
| `vbl_va001` | VBL-VA001: water pumps, normal / bearing / misalignment / 2 unbalance levels, triaxial | 3957 | 11871 | 3.80 GB | 1.8 GB |

### Run-to-failure (9)

Bearings recorded periodically until they fail.

| name | dataset | recordings | signals | download | on disk |
|---|---|---|---|---|---|
| `dlr_needle` | DLR: oscillating needle bearings, 8 run-to-failure tests x 2 bearings; acceleration, displacement, torque, force, temperature; use `--files` | ~9500 | ~100000 | 36.7 GB | ~7 GB |
| `femto` | FEMTO-ST PRONOSTIA: run-to-failure, 17 bearings | 27907 | 52796 | 1.2 GB | 0.2 GB |
| `ferrara_rtf` | Univ. Ferrara: 6 accelerated run-to-failure tests, self-aligning ball bearings, 5 s every 5 min | 12187 | 12187 | 12.1 GB | 12 GB |
| `ims` | NASA IMS: run-to-failure, 4 bearings on one shaft, 3 tests | 9464 | 46480 | 1.1 GB | 1.0 GB |
| `kaist_rtf` | KAIST: run-to-failure, 1 bearing, hourly vibration + temperature | 129 | 516 | 4.3 GB | 1.9 GB |
| `paderborn_rtf` | Paderborn University: 17 run-to-failure tests under random time-varying speed and load; use `--files` for a subset | 95660 | 191320 | 152 GB | ~38 GB |
| `unsw` | UNSW: run-to-failure with natural spall growth, 4 tests, measured at 4 speeds | 599 | 3594 | 9.7 GB | 8.0 GB |
| `wt_hss` | 2 MW wind turbine high-speed bearing (field): 50 daily snapshots until an inner race fault; CC BY-NC-SA | 50 | 100 | 0.22 GB | 0.16 GB |
| `xjtu_sy` | XJTU-SY: run-to-failure, 15 bearings, 3 operating conditions | 9216 | 18432 | 4.4 GB | 2.6 GB |

### Field data (1)

Real machines in operation.

| name | dataset | recordings | signals | download | on disk |
|---|---|---|---|---|---|
| `sca` | Pulp and paper mill (SCA): real machines measured daily for months | 6644 | 6644 | 0.84 GB | 0.2 GB |

*download* is what is fetched from the sources; *on disk* is the built dataset. Downloads are
kept in `<root>/_raw/` so datasets can be rebuilt without downloading again, so the space
needed is roughly **download + on disk** (you can delete `_raw/` if space is short, at the cost
of downloading again to rebuild). To store less, build only part of a dataset (see
[subsets](#quick-start)).

`bearing-datasets info <name>` shows the details, license and citation of each dataset (see
[License](#license)).

**Your own datasets** (e.g. private lab data) are built from files on your disk, without
changing the package. Write a `dataset.yaml` whose source points to the folder of raw files, and
a `builder.py` that reads them:

```yaml
sources:
  - {type: local, path: ~/data/my_rig, include: ["*.mat"]}
```

```bash
bearing-datasets build ~/my_datasets/my_rig   # first time, by the path of the definition
bearing-datasets info my_rig                   # afterwards, by name; bd.open("my_rig")
```

The full walkthrough is in [Private datasets](CONTRIBUTING.md#private-datasets), and a working
example is [`examples/private_datasets/my_cwru`](examples/private_datasets/my_cwru) (four CWRU
files read from a local folder).

## Concepts in one minute

* A **dataset** is one published dataset, e.g. `cwru`: `ds = bd.open("cwru")`.
* A **recording** is one acquisition: the machine ran in one state (its faults, speed and load)
  and one or more channels were recorded at the same time. Id: `recording_id`, e.g.
  `12k_DE_IR007_1`.
* A **channel** is one sensor, or one axis of a sensor, named as the dataset names it, e.g.
  `DE` (the drive-end accelerometer of CWRU).
* A **signal** is one channel of one recording. Id: `signal_id` = `<recording_id>/<channel>`,
  e.g. `12k_DE_IR007_1/DE`. Its samples are a numpy array: `ds.signal(signal_id)`; all the
  channels of a recording at once: `ds.recording(recording_id)`.
* The **metadata** is a table with **one row per signal**, saying what it is: the fault
  (`fault_type`, `fault_location`), the sensor (`sensor_location`, `quantity`, `axis`), the
  operating conditions (`speed_rpm`, `load`, …), the sampling rate, …

The sensor columns, for two datasets with different layouts:

| dataset | `channel` | `sensor_location` | `sensor_mounting` | `axis` | `quantity` |
|---|---|---|---|---|---|
| cwru | `DE` | `motor_bearing_de` | `casing` | `none` | `acceleration` |
| cwru | `FE` | `motor_bearing_nde` | `casing` | `none` | `acceleration` |
| cwru | `BA` | `base` | `base` | `none` | `acceleration` |
| mafaulda | `underhang_axial` | `test_bearing_de` | `pedestal` | `axial` | `acceleration` |
| mafaulda | `underhang_radial` | `test_bearing_de` | `pedestal` | `radial` | `acceleration` |
| mafaulda | `overhang_radial` | `test_bearing_nde` | `pedestal` | `radial` | `acceleration` |
| mafaulda | `microphone` | `ambient` | `none` | `none` | `sound_pressure` |

`channel` is the dataset's own name (to reproduce papers); `sensor_location` says **which
bearing or machine part** the sensor measures, with the same words in every dataset;
`sensor_mounting` says **what surface** it sits on; `axis` the measurement direction. Several
channels can share a location (a triaxial accelerometer is three channels).

## API

| code | what it does |
|---|---|
| `bd.set_root(folder)`, `bd.get_root()` | save / show the datasets folder (kept between sessions) |
| `bd.list_datasets()` | names of the available datasets |
| `ds = bd.open(name, root=None)` | open a built dataset |
| `ds.metadata(backend="pandas")` | metadata table (`backend="polars"` for polars) |
| `ds.columns()` | description of every column of this dataset |
| `ds.signal(signal_id, start=0, stop=None, unit=None, dtype=None)` | samples of one signal (numpy, original dtype and unit; `unit="g"` or `{quantity: unit}` converts, see [Units](#units)) |
| `ds.recording(recording_id, channels=None, unit=None, dtype=None)` | all channels of a recording, `{channel: array}` |
| `ds.iter_signals(signal_ids, unit=None, dtype=None)` | yields `(signal_id, array)`, one at a time |
| `ds.with_signals(meta=None, start=0, stop=None, unit=None, dtype=None)` | the metadata rows (default: all) with a `signal` column (numpy arrays); with `unit`, the `unit` column gives the converted units |
| `ds.signal_files()` | the Parquet files with the signals (to load them into a DataFrame) |
| `ds.cite()` | suggested citation of the dataset (check the source; see [License](#license)) |
| `bd.load_metadata(names)` | metadata of several datasets, with the columns they all have |
| `bd.build(name, root=None, force=False, channels=None, where=None, as_name=None, files=None)` | download and build a dataset or a subset of it (same as the CLI) |
| `bd.clean_raw(names=None, root=None, dry_run=False)` | delete the downloaded raw files of built datasets (`None`: all built) |

Command line (prefix with `uv run` if the command is not found):

| command | what it does |
|---|---|
| `bearing-datasets root [FOLDER]` | save the datasets folder (kept between sessions); without a folder, show the one in use |
| `bearing-datasets list` | every dataset, `[built]` for the ones ready in the folder |
| `bearing-datasets info NAME` | description, sources, size, license, citation and columns of a dataset |
| `bearing-datasets build NAME [NAME ...]` | download (cached, resumable) and convert one or more datasets; `--force` rebuilds |
| `bearing-datasets build NAME --as NEW [--channels CH ...] [--where COLUMN=V1,V2] [--files GLOB ...]` | build only part of a dataset under a new name: some channels, some recordings, or only the raw files matching the globs (to download less) |
| `bearing-datasets clean-raw NAME ... \| --all-built [--dry-run]` | delete the downloaded raw files of built datasets to free space (they keep working; a rebuild downloads again). `build --clean-raw` does it right after building |
| `bearing-datasets verify NAME` | re-hash the stored signals to check that the built files are intact |
| `--root DIR` (before the command) | use another datasets folder for this command only |

## The metadata table

One row per signal. These columns exist in **every** dataset:

| column | meaning |
|---|---|
| `dataset`, `signal_id` | ids |
| `recording_id` | groups the channels recorded at the same time |
| `native_label` | the label as the dataset names it (`IR007_1`, `KA04`, `IB`), for reproducing papers |
| `channel` | the channel name, as the dataset names it (`DE`, `CH14`, `underhang_axial`) |
| `sensor_location` | the bearing or machine part the sensor measures (see [Locations](#locations)) |
| `fs`, `n_samples` | sampling rate (Hz) and length |
| `fault_type` | fault(s) in the machine: `normal`, `inner`, `outer`, `rolling_element`, `cage`, `bearing`, `gear`, `shaft`, `unbalance`, `misalignment`, `looseness`, `electrical`, `other`, `unknown`, joined with `+` (`inner+outer`) |
| `fault_location` | the position of each faulty part, with the words of `sensor_location`, in the order of `fault_type` (`motor_bearing_de`, `test_bearing+gearbox`); `none` when normal |
| `sensor_at_fault` | `True` when the sensor is at a faulty position (computed from the two columns above) |
| `signal_file`, `signal_row_group`, `signal_row` | where the samples are stored |

Columns that only some datasets have, standard ones first:

| column | meaning | datasets |
|---|---|---|
| `quantity` | physical quantity: `acceleration`, `velocity`, `displacement`, `current`, `voltage`, `sound_pressure`, `speed`, `torque`, `force`, `temperature`, `angle`, `tachometer`, `encoder`, `time` (pulse times), `unknown` | all (and my_cwru) |
| `unit` | unit of the stored values (see [Units](#units)): a physical unit (`g`, `m/s^2`, `A`, …), `V` for an uncalibrated sensor, `counts` (raw ADC values), `normalized` (audio in [-1, 1]), `unknown` when not documented | all except cwru, hust, jnu |
| `sensitivity` | sensitivity of the sensor whose volts are stored (`100 mV/g`, `10 mV/A`); `none` when already in a physical unit, `unknown` when not documented | estogu, laspi |
| `axis` | measurement direction (`x`/`y`/`z`, `horizontal`/`vertical`, `axial`/`radial`/`tangential`) or phase (`a`/`b`/`c`); `none` for single-axis sensors | all except cwru, dcase_bearing, dlr, dlr_needle, fstf, hse_similar_system, hust, hust_transmission, isac, just_slewing, mfpt, ottawa_2018, ottawa_uored, paderborn, sca, sqv, uc204, uoemd, upm_citef, urma_crti, vibrobox, wt_hss |
| `sensor_mounting` | surface the sensor is on (ISO 20816-1): `pedestal` (stand-alone bearing housing), `casing` (machine casing at the bearing, e.g. a motor end shield), `outer_ring`, `shaft` (sensor on or probe aimed at the shaft), `base`; `none` without mechanical mounting (currents, microphones) | all (and my_cwru) |
| `speed_rpm` | shaft speed (rpm): measured, or the set or nominal speed when the dataset does not measure it (`ds.columns()` says which) | all except arkansas, army_pla, dcase_bearing, dlr_needle, hit_intershaft, hust_transmission, hustbearing, kaist_speed, mehran_uet, neepu, ottawa_2018, sdust, sqv, tecnalia_bearing, tecnalia_gearbox, uaq_upc, uoemd, urma_crti, vbl_va001, vibrobox, wt_hss (and my_cwru) |
| `speed_profile` | how the speed changes: `constant`, `increasing`, `decreasing`, `inc_dec`, `dec_inc`, `varying`, `unknown` | army_pla, hust_transmission, hustbearing, kaist_speed, mcc5_thu_gearbox, mcc5_thu_motor, ottawa_2018, sdust, sqv, tecnalia_bearing, tecnalia_gearbox, uaq_upc, uoemd, vibrobox |
| `load`, `load_unit` | load applied to the machine, in `load_unit` (hp, W, N, kN, Nm, …) | adelaide, bjtu_bogie, cwru, dirg, dlr, dlr_needle, femto, ferrara_or, ferrara_rtf, haust_ldv, hse_similar_system, hust, im_vacd, ims, just_slewing, kaist_load, kaist_rtf, laspi, lenze_mb, mcc5_thu_gearbox, mcc5_thu_motor, mfpt, neepu, ottawa_uored, paderborn, paderborn_rtf, sdust, uc204, upm_citef, xjtu_sy |
| `operating_condition` | the dataset's own id of the operating regime (e.g. FEMTO `1`, XJTU `35Hz12kN`, Paderborn `N15_M07_F04`), for cross-condition tests | army_pla, bjtu_bogie, cumtb_pitch, femto, haust_ldv, hse_similar_system, hust_transmission, hustbearing, mehran_uet, paderborn, phm09, saarland, sdust, seu, tecnalia_bearing, tecnalia_gearbox, uoemd, xjtu_sy |
| `fault_origin` | `artificial` (seeded) or `real` (grown in operation); `none` if healthy | adelaide, arkansas, army_pla, cumtb_pitch, cwru, dirg, dlr, estogu, ferrara_or, fstf, haust_ldv, hit_intershaft, hit_sm, hse_similar_system, hust, hustbearing, im_vacd, jnu, just_slewing, kimm_pmsm, neepu, paderborn, saarland, sdust, sqv, subf_v1, subf_v2, susu, tecnalia_bearing, uaq_upc, uc204, uestc, uos, upm_citef, vbl_va001, vit_sq, vit_taper |
| `fault_size_mm` | fault size in mm; 0 if healthy | cwru, dirg, dlr, ferrara_or, haust_ldv, hustbearing, jnu, mehran_uet, saarland, sdust, uc204 |
| `fault_severity` | fault severity in the dataset's own words (see `ds.columns()`); `not graded` for a fault the dataset does not grade, `none` if healthy | cwru, dirg, dlr, ferrara_or, haust_ldv, hit_intershaft, hit_sm, hustbearing, kaist_load, lenze_mb, mcc5_thu_gearbox, mcc5_thu_motor, mehran_uet, nln_emp, ottawa_uored, paderborn, sdust, sqv, uaq_upc, uc204, uos, upm_citef |
| `fault_severity_level` | severity rank: 0 healthy, 1, 2, … from the mildest, within the dataset and fault type; 1 if not graded (not comparable across datasets) | cwru, dirg, dlr, ferrara_or, haust_ldv, hit_intershaft, hit_sm, hustbearing, kaist_load, lenze_mb, mcc5_thu_gearbox, mcc5_thu_motor, mehran_uet, nln_emp, ottawa_uored, paderborn, sdust, sqv, uaq_upc, uc204, uos, upm_citef, vbl_va001 |
| `bearing_id` | physical bearing tested: the same id means the same bearing (for grouped train/test splits) | cwru, ferrara_or, hit_intershaft, hse_similar_system, hust, hustbearing, ottawa_uored, paderborn, saarland |
| `bearing_model` | bearing designation (e.g. `6205-2RS`), per sensor when the bearings differ | all except adelaide, arkansas, cumtb_pitch, dcase_bearing, dirg, dlr_needle, estogu, femto, hit_intershaft, im_vacd, isac, jnu, just_slewing, kimm_pmsm, laspi, mafaulda, neepu, nln_emp, ottawa_uored, seu, subf_v1, subf_v2, uaq_upc, unsw, urma_crti, vit_taper, wt_hss |
| `bpfo`, `bpfi`, `bsf`, `ftf` | bearing fault frequencies in orders of the shaft speed (Hz = order × rpm / 60), of the test bearing (nearest the sensor when several are documented); `bsf` is the ball spin frequency (rolling element defects show at 2 × `bsf`) | army_pla, cwru, dirg, dlr, femto, ferrara_or, ferrara_rtf, haust_ldv, hust, hust_transmission, hustbearing, ims, kaist_load, kaist_rtf, kaist_speed, laspi, lenze_mb, mafaulda, mcc5_thu_gearbox, mcc5_thu_motor, ottawa_2018, ottawa_uored, paderborn, paderborn_rtf, phm09, saarland, sca, sdust, susu, tecnalia_bearing, tecnalia_gearbox, uos, upm_citef, vbl_va001, vit_sq, xjtu_sy |
| `repetition` | index of acquisitions repeated with the same settings | arkansas, just_slewing, laspi, nln_emp, ottawa_2018, paderborn, phm09, sdust, uaq_upc, upm_citef, vit_taper |
| `run_id` | run-to-failure experiment | dlr_needle, femto, ferrara_rtf, ims, kaist_rtf, paderborn_rtf, unsw, wt_hss, xjtu_sy |
| `time_s`, `rul_s` | time since the start of the run and remaining useful life (s) | dlr_needle, femto, ferrara_rtf, ims, kaist_rtf, paderborn_rtf, wt_hss, xjtu_sy |
| `accelerometer_fs_set` | accelerometer rate requested from the phone, Hz | im_vacd |
| `acoustic_fs_set` | microphone rate requested from the phone, Hz | im_vacd |
| `acquisition` | stationary, repetition 1 or 2 | dirg |
| `added_mass_g` | load in grams from the file name (0, 6, 12), presumably masses added on the balance rotor | vit_sq |
| `amplitude_deg` | oscillation amplitude in degrees | dlr_needle |
| `asset` | type of machine (Roller, Engine, Pump, Strainer, Agitator) | sca |
| `bearing_manufacturer` | manufacturer of the test bearing (FAG, IBU, MTK) | paderborn |
| `bearing_type` | deep groove ball, cylindrical roller or tapered roller | uos |
| `belt_tension` | belt tension setting giving the radial force, 250 or 500 (stated as Nm, likely N) | lenze_mb |
| `cage` | plastic or metal | hse_similar_system |
| `case` | case number 1-11 (one machine and one fault per case) | sca |
| `chunk` | number of the ~26 s chunk within the 10 min acquisition | cumtb_pitch |
| `coupling_mounting` | assembly deviation code of the coupling mounting (0-2 | saarland |
| `damage` | how the damage was made: EDM, drilling, electric engraver (artificial) or pitting, indentation (real, from accelerated lifetime tests) | paderborn |
| `damage_length_mm` | length of the inner ring defect (0 if undamaged) | saarland |
| `dcase_split` | train (normal only) or test, as in the challenge | dcase_bearing |
| `defect_depth_um` | defect depth in micrometres (110 slope series, 100 length series) | adelaide |
| `defect_length_deg` | angular length of the defect for the length series | adelaide |
| `defect_slope_deg` | entry and exit slope of the defect edges in degrees (90 = square edges) | adelaide |
| `depth_ir_mm` | depth of the inner race defect (0 if none) | upm_citef |
| `depth_or_mm` | depth of the outer race defect (0 if none) | upm_citef |
| `depth_re_mm` | depth of the rolling element defects (0 if none) | upm_citef |
| `disturbance` | none, or noise_1 to noise_5 (physical disturbances, presumably D1-D5) | kimm_pmsm |
| `domain` | source or target domain | dcase_bearing |
| `dynamic_load_peak_n` | peak of the measured dynamic (shaker) load in N | paderborn_rtf |
| `factory_noise` | factory noise attribute A or B (none if not given) | dcase_bearing |
| `failed_bearing` | bearing(s) that failed at the end of the test | ims |
| `failure` | failure found at the end of the test, in words | ims, paderborn_rtf, xjtu_sy |
| `fault_arc_deg` | arc of the raceway covered by the fault, in degrees (2, 5, 8 | hit_sm |
| `fault_depth_mm` | depth of the wire-cut fault (0 if healthy) | hit_intershaft |
| `fault_detail` | the faults of the recording in words, from the health codes | bjtu_bogie, cumtb_pitch, phm09, seu, uoemd, vit_taper |
| `fault_length_mm` | length of the wire-cut fault (0 if healthy) | hit_intershaft |
| `field_data` | true for the 3 real-world recordings, false for the test rig | mfpt |
| `file_series` | main, or z for the files whose name carries "_z" (not explained by the authors) | vbl_va001 |
| `fixed_speed` | true when the machine runs at a fixed speed | sca |
| `force_level` | radial load level 0-3 (about 0, 1600, 2500, 3300 N) | saarland |
| `gear_type` | spur or helical | phm09 |
| `hp_rpm` | high-pressure rotor speed in rpm | hit_intershaft |
| `imbalance_g` | added unbalance mass in grams (0 if none) | mafaulda |
| `kimm_folder` | original folder (e.g | kimm_pmsm |
| `load_level` | High or Low load | phm09 |
| `load_position` | resistor bank switch position 0-5 | estogu |
| `load_resistance` | resistance of that position (no load, 111, 56, 38, 29, 23 ohm) | estogu |
| `load_setting` | load setting of the file name (0 or 2 V) | seu |
| `load_state` | unloaded, or loaded (a disk bolted to the shaft) | uoemd |
| `lp_rpm` | low-pressure rotor speed in rpm | hit_intershaft |
| `lubrication` | Oil1, Oil2, Oil3 or NoOil | dlr_needle |
| `machine_running` | false when the dataset marks the measurement as machine off / speed missing (label -1) | sca |
| `measured_at` | date and time of the snapshot (from the file name) | ims, sca |
| `measurement` | vibration or electric (separate acquisition systems) | nln_emp |
| `measurement_batch` | measurement batch 1-48 | saarland |
| `measurement_day` | measurement day number | saarland |
| `mic_location` | microphone location attribute A-D (none if not given) | dcase_bearing |
| `misalignment_direction` | horizontal, vertical or none | mafaulda |
| `misalignment_mm` | shaft misalignment in mm (0 if none) | mafaulda |
| `mounting_position` | mounting position of the test bearing, A-D | saarland |
| `n_files` | number of consecutive storage files joined into the recording | uestc |
| `official_set` | learning (learning set), test (in the truncated official test set) or hidden (after the truncation) | femto |
| `or_position` | position of an outer race fault relative to the load zone (6:00 centered, 3:00 orthogonal, 12:00 opposite) | cwru |
| `original_recording` | number of the recording in the original 300-recording set (Data_No there), 0 if new in the extension | hse_similar_system |
| `oscillation_hz` | oscillation frequency in Hz | dlr_needle |
| `phone` | iphone_13, galaxy_s6 or galaxy_a50 | im_vacd |
| `phone_mounting` | hand_held or rigid | im_vacd |
| `radial_force_n` | radial force on the test bearing in N (F04 = 400, F10 = 1000) | paderborn |
| `rig` | spectraquest (SpectraQuest MFS) or self_built | hit_sm, hse_similar_system |
| `rul_cycles` | shaft revolutions left until the last measurement of the test | unsw |
| `run` | sensor-mounting run 1-3 | saarland |
| `sca_label` | label exactly as in the dataset (-1 off, 0 normal, 1 inner, 2 ball, 3 outer) | sca |
| `second_shaft` | 1 if the second shaft was used (0/1 | saarland |
| `section` | DCASE section 00-02 (each with its own domain shift) | dcase_bearing |
| `segment` | number of the 20480-sample segment within the test and speed pair | hit_intershaft, subf_v1, subf_v2 |
| `sensor_mounting_deviation` | assembly deviation code of the sensor mounting (0/1 | saarland |
| `sensor_position` | accelerometer position on the housing, S (12 o'clock), C (2), B (11) or A (9) | kimm_pmsm, sca |
| `series` | slope (defect entry/exit slope series) or length (defect length series) | adelaide |
| `session` | stationary (speed and load combinations) or endurance (230 h monitoring) | dirg |
| `setup` | motor_2 or motor_4 (motor-pump set) | nln_emp |
| `shaft_cycles` | shaft revolutions since the start of the test (from the file name) | unsw |
| `snapshot` | number of the snapshot in the test (as in the file names) | dlr_needle, femto, xjtu_sy |
| `source_file` | original CWRU file (e.g | cwru, mfpt, my_cwru, sca |
| `speed_pct` | motor speed in % of rated speed | nln_emp |
| `speed_setting` | speed setting of the folder (25, 50 or 75 | arkansas, vibrobox |
| `stethoscope` | yes if recorded through a stethoscope (Datasets 1), no otherwise (Datasets 2) | fstf |
| `study` | 2020, 2021 or 2023 (Zenodo record) | upm_citef |
| `subset` | bearing, gearbox or mixed (the folder of the file) | army_pla, seu, vibrobox |
| `supply` | inverter (With_Driver) or grid (Without_Driver) | estogu |
| `supply_hz` | supply frequency in Hz | estogu, laspi, uaq_upc, urma_crti |
| `temperature_room_c` | mean room temperature in degC | paderborn_rtf |
| `temperature_t1_c` | mean bearing temperature at position T1 in degC | paderborn_rtf |
| `temperature_t2_c` | mean bearing temperature at position T2 in degC | paderborn_rtf |
| `test` | stationary (37.5-50 min depending on the channel) or start-up (30 s) | uaq_upc |
| `trial` | run number 0-6 (varying speed), or constant (the 600 s run at 3010 rpm) | kaist_speed |
| `unbalance_gcm` | unbalance in gram.cm (6 or 27 | vbl_va001 |
| `velocity` | rotation velocity attribute from the file name (none if not given) | dcase_bearing |
| `worker` | worker who mounted the bearing, 1 or 2 | saarland |

`ds.columns()` (or `bearing-datasets info <name>`) gives the exact meaning of every column in a
dataset, including dataset notes such as how `bearing_id` was defined.

### Locations

`sensor_location` and `fault_location` use one vocabulary, `<unit>_<item>[_<position>]`, built
from the terms of ISO 14224 (equipment units and maintainable items), IEC 60034-7 (drive end
`de`, non-drive end `nde`) and ISO 20816-1 (measurement at each bearing):

| part | values |
|---|---|
| unit | `motor`, `gearbox`, `pump`, `generator`, `axle` (railway wheelset), `machine` (a machine whose type the location does not say), `rig` (the structure and shaft line of a test rig) |
| item | `bearing`, `shaft`, `rotor`, `stator`, `gear`, `impeller`, `supply` (the currents and voltages feeding a motor) |
| position | `de`, `nde`; gearbox shaft stages `input`, `intermediate`, `output`; `left`, `right` |
| test rigs | `test_bearing` (the bearing under study: seeded fault, swapped or run to failure), `support_bearing` (the rig's own bearings), with `_de` / `_nde` when there are two |
| others | `coupling`, `base` (base plate), `ambient` (off the machine: microphones, room temperature), `unknown` |

A location names the bearing or part measured, not the surface: a sensor on the housing of the
drive-end motor bearing is at `motor_bearing_de`, with `sensor_mounting` = `casing`. The full
list is `bearing_datasets.schema.LOCATIONS`.

Three rules to keep in mind:

* **No missing values.** When a value does not apply the table says `none` (e.g.
  `fault_origin` of a healthy bearing); when the dataset does not document it, `unknown`.
* **`fault_type` describes the machine, not the sensor.** A CWRU fan-end signal recorded with a
  faulty drive-end bearing has `fault_type="inner"`, `fault_location="motor_bearing_de"`,
  `sensor_location="motor_bearing_nde"` and `sensor_at_fault=False`.
* **No train/test splits are included.** They belong to each study; use `bearing_id` (or
  `recording_id`) to split without leakage.

Bearing fault frequencies (BPFO, BPFI, …) are in each dataset's description.

### Units

Signals keep the values of the raw files; `unit` says what they are in. Pass `unit=` to the
signal readers to convert:

```python
ds.signal(sid, unit="m/s^2")                                   # one unit
ds.with_signals(meta, unit={"acceleration": "g", "speed": "Hz"})  # per quantity, others as stored
```

| dimension | units |
|---|---|
| acceleration | `m/s^2`, `mm/s^2`, `g` (9.80665 m/s^2) |
| velocity | `m/s`, `mm/s`, `um/s`, `in/s` |
| displacement | `m`, `mm`, `um`, `mil` |
| electrical | `V`, `mV`, `A`, `mA` |
| mechanical | `N`, `kN`, `Nm`, `Pa`, `rpm`, `Hz` (shaft speed, rev/s), `rad`, `deg`, `rev`, `s`, `ms` |
| not convertible | `degC`, `dB`, `counts` (raw ADC values), `normalized` (audio in [-1, 1]), `unknown` |

Signals stored in `V` are converted through the `sensitivity` column when the dataset documents
it (`100 mV/g`). A unit change never integrates: acceleration does not become velocity.
Converting a signal whose unit is `unknown`, `counts`, or another dimension raises `ValueError`.
Converted samples are float64 (`dtype=np.float32` to save memory).

## On disk

```
<root>/
  _raw/                           downloaded files, shared by all datasets and users
  <dataset>/
    metadata.parquet              one row per signal
    signals/part-<dtype>.parquet  signal_id + signal, zstd compressed
    manifest.json                 sources used, raw file checksums, content hash, citation,
                                  column descriptions
```

The metadata can be read without this library: `pd.read_parquet(f"{root}/cwru/metadata.parquet")`.

## Documentation

* [docs/guide.md](docs/guide.md): concepts, recipes (windows, splits, resampling, several
  datasets, PyTorch), notes on each dataset, FAQ
* [examples/usage.ipynb](examples/usage.ipynb): a runnable guided tour (download it and open it
  in any Jupyter environment where the package is installed)
* [CONTRIBUTING.md](CONTRIBUTING.md): add a public dataset to the package, or build a private
  one (internal lab data) without changing this repository

## Add your dataset

Contributions are welcome! If you published a bearing or rotating-machinery dataset, or know
a public one that is missing, please add it: it makes the data easier to find, to compare and
to cite. A dataset is a folder with a short `dataset.yaml` (sources, license, citation) and a
`builder.py` that reads the raw files. [CONTRIBUTING.md](CONTRIBUTING.md) explains the steps.
You can also open an issue with a link to the data and we will look into adding it.

## Development with AI

This library was developed with the help of AI coding assistants (Claude Code). The code,
dataset definitions and documentation were reviewed, and the builds were checked against the
original records, but errors can still occur. If you find one (a wrong label, count, sampling
rate, license or description, or a bug), please
[open an issue](https://github.com/VictorBauler/BearingDatasets/issues).

## Citing

If this library helps your work, please cite it, together with **each dataset you use**
(`ds.cite()` or `bearing-datasets info <name>`; see [License](#license)). Citing the
repository lets others find the same data and reproduce your results.

```bibtex
@software{bauler_bearing_datasets,
  author  = {Bauler, Victor},
  title   = {bearing-datasets: public bearing fault datasets in one common format},
  year    = {2026},
  doi     = {10.5281/zenodo.23062167},
  url     = {https://github.com/VictorBauler/BearingDatasets}
}
```

This DOI always points to the latest version; each release also has its own DOI, listed on
[Zenodo](https://doi.org/10.5281/zenodo.23062167), to cite the exact version you used.

## License

The **code** of this repository is released under the MIT license (see [LICENSE](LICENSE)),
provided **"as is", without warranty**, including for the correctness of the downloaded data
and of its labels. The MIT license covers the code only, **not the datasets**.

This repository does not contain or redistribute any dataset. It holds code and metadata
(download addresses, checksums, descriptions). The data is downloaded **by you**, from the
source published by each dataset's authors (or a public mirror of it), when you run `build`.

* **Every dataset keeps its own license and terms.** This package grants no rights on the data.
  **You are responsible for confirming the license** of each dataset you use, on its original
  page (`bearing-datasets info <name>` shows the source and a summary of the license), and for
  respecting it.
* Licenses differ a lot between datasets. Some allow any use with attribution (e.g. CC BY),
  some forbid commercial use (e.g. CC BY-NC, including inside a company's products or
  services), and some state no license at all. Without a license, the authors keep all rights:
  ask them before any commercial use or redistribution.
* **Cite the authors** of every dataset you use. Most licenses (CC BY) require it. The
  citation given by `ds.cite()` and `bearing-datasets info` is a **suggestion**: besides the
  dataset itself, it may include a paper that is not the dataset's own reference (e.g. the
  Smith & Randall benchmark study for CWRU). Check the original source for the citation its
  authors ask for.
* **Do not redistribute** built datasets (the Parquet files) or the download cache (`_raw/`)
  unless the dataset's license allows it. Sharing a built folder inside your own team is fine
  as long as every user respects the licenses.
* The license, description and labels of each dataset in this repository are **summaries made
  in good faith**. They may be incomplete or out of date. The original source and its authors are
  authoritative.
* This project is **not affiliated with or endorsed by** the dataset authors or their
  institutions. Their names are used only to identify the datasets.

**Dataset authors:** if you want your dataset removed from this library, or described
differently, [open an issue](https://github.com/VictorBauler/BearingDatasets/issues) and we
will do it. If you want it added, see [Add your dataset](#add-your-dataset).
