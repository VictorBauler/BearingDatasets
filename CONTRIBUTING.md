# Contributing

Thanks for helping! Every dataset added here saves the next person from writing the same
download-and-parse code again. You can contribute in several ways:

* **Suggest a dataset**: open an issue with a link to the data, the paper and the license. No
  code needed; someone else may add it.
* **Report a problem**: a wrong label, a broken link, a source that changed, a mistake in a
  description. Open an issue with the dataset name and what you saw.
* **Add a dataset**: follow [Adding a dataset](#adding-a-dataset) below.
* **Improve the code or the docs**: open a pull request (see [Changing the code](#changing-the-code)).

## Getting started

You need [git](https://git-scm.com) and [uv](https://docs.astral.sh/uv/). Fork
[the repository](https://github.com/VictorBauler/BearingDatasets) on GitHub, then:

```bash
git clone https://github.com/<your-user>/BearingDatasets && cd BearingDatasets
uv sync                        # package + test and notebook tools
uv run pytest                  # fast tests, should all pass
git checkout -b add-<name>     # one branch per dataset or change
```

## Adding a dataset

### Is it a good fit?

A dataset can be added when:

* it holds **raw waveforms** (vibration, current, acoustic, ...), not only features, images,
  spectrograms or SCADA tables;
* its files can be **downloaded without a login** (Zenodo, Mendeley Data, Kaggle datasets,
  Dataverse, a university page, ...), in an open format (`.mat`, `.csv`, `.txt`, `.tdms`, ...);
* each recording can be **labelled**: which fault (or none), where, and under which operating
  conditions.

Any license can be listed: the package does not redistribute the data, and the license is
shown to users (`bearing-datasets info`). Just report it faithfully.

### Steps

1. **Read the paper and the data record.** Note the test rig, the sensors, the sampling rates,
   the fault labels and the file layout. Download a few files by hand and open them.
   When the files disagree with the documentation (sampling rate, counts, durations, labels),
   **trust the files** and say so in `description`.
2. Create `src/bearing_datasets/datasets/<name>/` (lowercase, `_` between words) with
   [`dataset.yaml`](#datasetyaml-where-the-data-comes-from) and
   [`builder.py`](#builderpy-turn-raw-files-into-rows). Copy an existing dataset with a similar
   source as a starting point.
3. [Build it](#build-and-check) into a scratch folder and check the result.
4. [Update the README](#update-the-readme).
5. [Open a pull request](#open-a-pull-request).

### `dataset.yaml`: where the data comes from

```yaml
name: hust
title: HUST bearing dataset (Hanoi)
description: |                 # the rig, sensors, labels, and anything surprising in the files
  ...
license: CC-BY-4.0             # as stated by the authors; "unspecified" if none
homepage: https://data.mendeley.com/datasets/cbv7jyx4p9/3
size: "download 0.67 GB, built 0.30 GB (measured)"
citation: "Thuan & Hong (2023). HUST bearing ... doi:10.17632/cbv7jyx4p9.3"
sources:                       # tried in order, file by file (add mirrors below the official one)
  - {type: mendeley, id: cbv7jyx4p9, version: 3, include: "HUST bearing dataset/*.mat",
     strip_prefix: "HUST bearing dataset/"}
columns:                       # describe every column that is not a standard one
  bearing_model: bearing type, 6204 to 6208
  load: motor load in W (0, 200 or 400)     # optional note on a standard column
```

Every column your builder produces must be described: the standard ones are described in
`schema.py`, the others under `columns:` (the build stops if one is missing). You can also
add a note to a standard column, e.g. to say what `fault_severity` means in your dataset.

Source types:

| type | fields |
|---|---|
| `mendeley` | `id`, `version`, `include` |
| `zenodo` | `record`, `include` |
| `kaggle` | `dataset` (`owner/slug`), `version`, `include`; public datasets need no Kaggle account. `bundle: true` downloads the whole version as one zip (`<slug>.zip`), better for datasets of thousands of files |
| `dataverse` | `server` (e.g. `https://dataverse.csuc.cat`), `doi`, `version` (e.g. `"2.1"`), `include`; works with any Dataverse repository. Tables that Dataverse converted to `.tab` are downloaded as uploaded (e.g. `.csv`), under their original name |
| `http` | `base_url`; also list the files with `files: [a.mat, b.mat]` (or `files: table.csv:column`). Or `urls: {file name: url}` when each file has its own link (e.g. Google Drive) |
| `local` | `path`, `include` (data already on the server) |

Files are downloaded four at a time (`DOWNLOAD_WORKERS` in `sources.py`). `.zip` and `.rar` files are extracted automatically: `K001.rar` becomes the folder `K001/`.
Add `extract: false` to keep archives as they are (e.g. very large or split zips that the
builder reads directly, like `bjtu_bogie`).

### `builder.py`: turn raw files into rows

```python
from bearing_datasets.io import read_mat

CHANNELS = {  # per channel: at least sensor_location and fs
    "vibration": {
        "sensor_location": "test_bearing",  # which bearing or part (README: Locations)
        "sensor_mounting": "pedestal",      # on its housing
        "quantity": "acceleration",
        "fs": 51200,
    },
}


def recordings(raw_dir):
    for path in sorted(raw_dir.glob("*.mat")):
        code = path.stem[:-3]
        yield {
            "recording_id": path.stem,
            "native_label": code,
            "fault_type": "normal" if code == "N" else "inner",  # see README for the values
            "fault_location": "none" if code == "N" else "test_bearing",
            "speed_rpm": 1500.0,                                  # any other column you want
            "signals": {"vibration": read_mat(path)["data"].ravel()},
        }
```

* Yield one dict per recording. Every key except `signals` becomes a column of all its
  signals.
* If the sampling rate changes per recording, add `"fs": 48000` (or `{"DE": 48000}`) to the dict.
  More generally, a key of the recording dict overrides the same key of `CHANNELS` (e.g. a
  `sensor_location` that changes per recording), and any value can be given per channel as
  `{channel: value}` (e.g. the fault frequencies of the bearing each sensor is on).
* Bearing fault frequencies (`bpfo`, `bpfi`, `bsf`, `ftf`, in orders of the shaft speed,
  `bsf` = ball spin frequency): compute them with
  `bearing_datasets.bearings.fault_orders(balls, ball_d, pitch_d, contact_deg)` from the
  geometry in the dataset's documents or the manufacturer's catalogue, and say where it comes
  from in a `columns:` note. Leave them out if the bearing is not known.
* Use the standard column names from the README when they apply (`speed_rpm`, `load`,
  `operating_condition`, `bearing_id`, `bearing_model`, `fault_severity`, `repetition`, …),
  and the standard vocabularies for `fault_type`, `sensor_location` / `fault_location`,
  `sensor_mounting`, `quantity`, `axis`, `speed_profile` and `fault_origin`
  (`bearing_datasets.schema.VOCABULARIES`; the build checks them). `sensor_at_fault` is
  computed for you.
* `unit` is the unit the stored values are in, from `bearing_datasets.units.UNITS`; it must fit
  the `quantity` (the build checks it). A unit needs a source: the file header, the record or
  the paper, or a clear check of the values (e.g. a z axis with a mean of 1 in g); say which in
  the description, and write `unknown` rather than guess. Keep sensor volts as `V` and give
  the documented sensitivity in `sensitivity` (`"100 mV/g"`, `"10 mV/A"`; `"none"` for
  channels already in a physical unit, `"unknown"` when not documented), so that
  `ds.signal(..., unit="g")` can convert them. Integer ADC values are `counts`.
* Name a new column like the standard ones: `<subject>_<attribute>[_<unit>]`, with the unit
  at the end when it is fixed (`fault_depth_mm`, `radial_force_n`), `_id` for an identifier,
  `_level` for an ordinal integer (0 = healthy). Avoid
  the bare word "condition": `operating_condition` is the regime, `fault_type` the fault.
* Locations: name the bearing or part the sensor measures, as precisely as the dataset says
  (`motor_bearing_de`, `gearbox_bearing_input`, `test_bearing`), and put the surface it is on
  in `sensor_mounting`. Use the same words for `fault_location`, so that `sensor_at_fault`
  works. Fall back to the unit (`motor`, `gearbox`), then `machine`, then `unknown`.
* `fault_severity_level`: when the dataset grades its faults, rank the grades within each
  fault type from 1 (mildest); 0 is healthy, and a fault that is not graded is 1
  (`fault_severity="not graded"`).
* **No missing values**: a column must have a value in every row. Use `"none"` when it does
  not apply (e.g. `fault_location` of a healthy recording), `"unknown"` when the dataset does
  not say, and leave the column out if it only makes sense for some rows. The build stops
  with an error if a value is missing.
* Large recordings: a signal can be a function that returns the array
  (`"signals": {"CH1": lambda: read_channel(...)}`). It is only called if that channel is
  stored, so subset builds (`--channels`, `--where`) skip the reading work too.
* Put tables of facts in a CSV next to the builder (see `cwru/files.csv`,
  `paderborn/bearings.csv`).

### Build and check

```bash
uv run bearing-datasets --root ~/scratch build <name>   # the first build writes files.lock.json
```

Build into a scratch folder, not a shared one. The build validates the metadata (vocabulary,
no missing values, every column described) and stops with a clear message if something is
wrong. Then open it and compare with the paper and the record:

```python
import bearing_datasets as bd
ds = bd.open("<name>", root="~/scratch")
meta = ds.metadata()
meta.recording_id.nunique(), len(meta)                              # counts as documented?
meta.groupby("channel")[["fs", "n_samples"]].agg(["min", "max"])    # rates and lengths
meta.drop_duplicates("recording_id").fault_type.value_counts()      # label balance
ds.signal(meta.signal_id.iloc[0])                                  # same values as the raw file?
```

* Signals keep their original values and dtype: no resampling, scaling or normalisation.
* Write the measured sizes in `size:` (download, and the built folder).

### Update the README

The tests check that the README lists every dataset. Add:

* a row for the dataset in the right group of the [dataset tables](README.md#datasets), and
  update the group count, the "**N datasets**" line and the "**N public**" headline;
* the dataset to the "datasets" cell of every column it has in the "Columns that only some
  datasets have" table, and a row for each of its own columns (those not in `schema.py`).

Optionally, add a note to [docs/guide.md](docs/guide.md) §6 for anything users should know.

### Open a pull request

```bash
uv run pytest
uv run ruff check src tests && uv run ruff format --check src tests
```

Commit `dataset.yaml`, `builder.py`, `files.lock.json` (the pinned checksums) and any CSV, in
one commit per dataset. **Never commit data.** In the pull request, say how you checked the
build (counts, a few signal values) and anything that differs from the paper.

If a dataset turns out not to be a good fit (labels that cannot be mapped, no raw data, a login
needed), a short issue explaining why is useful too: it saves the next person the work.

## Changing the code

* Add a test for every change (`tests/test_build.py`, `tests/test_sources.py`); `uv run pytest`
  and ruff (line length 100) must pass. `uv run pre-commit install` runs ruff on each commit.
* The code runs on Linux, macOS and Windows: pass `encoding="utf-8"` to every text read or
  write, and do not rely on symlinks.

## Private datasets

A dataset built from your own files (internal lab data, confidential measurements, or public
files you downloaded by hand) needs **no change to this repository**: only the installed
package. A complete, working example is
[`examples/private_datasets/my_cwru`](examples/private_datasets/my_cwru) (four CWRU files).

### Overview

Three folders are involved:

```text
~/data/my_rig/                 raw files, as you have them (only read, never changed)
    run1.mat  run2.mat  ...
~/my_datasets/my_rig/          the definition: dataset.yaml + builder.py (+ files.lock.json)
/data/bearing_datasets/        your root folder: where every dataset is built
    my_rig/                    the built dataset (metadata.parquet, signals/)
    _raw/sha256/...            a copy of the raw files, checked by checksum
```

1. **Point to the raw files** with a `local` source in `dataset.yaml`:

   ```yaml
   sources:
     - type: local
       path: ~/data/my_rig          # absolute, ~, or {root}/... (inside the root folder)
       include: ["*.mat"]           # optional glob(s), relative to path; default: every file
   ```

   Every file under `path` that matches `include` (subfolders too) is part of the dataset, under
   its path relative to `path` (e.g. `run1.mat`, `day2/run7.mat`).

2. **Write `builder.py`** as for a public dataset ([above](#builderpy-turn-raw-files-into-rows)).
   `recordings(raw_dir)` sees the files with the same relative paths:
   `raw_dir / "day2/run7.mat"`. Archives (`.zip`, `.rar`, ...) are also extracted next to
   themselves (`day2.zip` -> `day2/`), as for downloaded data.

3. **Build it by path** the first time:

   ```bash
   bearing-datasets build ~/my_datasets/my_rig
   ```

   The build lists the files, writes `files.lock.json` (names, sizes, sha256) next to
   `dataset.yaml`, copies the files into `<root>/_raw/`, and runs the builder. Keep
   `files.lock.json` with the definition (e.g. in your private repository).

4. **Use it by name** afterwards: the build remembers the definition folder.

   ```python
   ds = bd.open("my_rig")
   ```

   `bearing-datasets list` shows it as "built, not part of the package";
   `bearing-datasets info my_rig` and `bearing-datasets build my_rig --force` also work by
   name. If the definition folder moves, build once more with the new path.

### When the raw files change

Builds always use the files in `files.lock.json`:

* a **changed** file stops the build with `checksum mismatch`;
* a **new** file is ignored.

To accept the new state of the folder, delete `files.lock.json` and rebuild with `--force`.

### Sharing

Keep the definition folder where the other users of the root can read it (e.g. a shared folder
on the server, not your home folder); otherwise only you can rebuild it by name. The built
dataset and the copies in `<root>/_raw/` contain your data: share the root folder only with
people allowed to see it.
