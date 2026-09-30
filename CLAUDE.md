# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

## What this is

`bearing-datasets`: a Python package + CLI that downloads public bearing / rotating-machinery
fault datasets from their original sources (pinned by sha256) and converts each one into the
same format: one `metadata.parquet` (one row per signal = one channel of one recording)
plus `signals/part-<dtype>.parquet`. Built once into a datasets folder (the root, often
shared on a server), then read with `bd.open(name)`.

User docs: `README.md` (dataset list, API and CLI tables, column tables), `docs/guide.md`
(concepts, recipes, per-dataset notes, FAQ), `CONTRIBUTING.md` (how to add a dataset).
Keep them in sync with the code; do not duplicate their content here.

## Commands

```bash
uv sync                                   # package + dev tools
uv run pytest                             # fast tests (integration tests are deselected)
uv run ruff check src tests && uv run ruff format --check src tests
uv run bearing-datasets --root ~/scratch build <name>   # build into a scratch root
BEARING_DATASETS_ROOT=~/scratch uv run pytest -m integration   # checks built datasets
```

When chaining tests with a commit, use `set -o pipefail` (a `| tail` otherwise hides a
failing pytest/ruff and the commit goes through).

## Code map

- `src/bearing_datasets/sources.py`: source types (`http`, `mendeley`, `zenodo`, `kaggle`,
  `dataverse`, `local`), listing, the shared download cache `<root>/_raw/sha256/<digest>`,
  resumable downloads (`DOWNLOAD_WORKERS` files at a time), archive extraction, `make_lock`.
- `src/bearing_datasets/build.py`: `build()` (lock -> stage raw -> run the builder ->
  validate -> write Parquet + `manifest.json`), subsets (`channels`, `where`, `files`,
  `as_name`), `clean_raw()`.
- `src/bearing_datasets/schema.py`: `REQUIRED` and `OPTIONAL` columns, the `CONDITIONS`
  vocabulary, `validate()`.
- `src/bearing_datasets/dataset.py`: reading (`Dataset`, `open`, `load_metadata`, root config).
- `src/bearing_datasets/cli.py`: `root | list | info | build | clean-raw | verify`.
- `src/bearing_datasets/datasets/<name>/`: one folder per dataset: `dataset.yaml`,
  `builder.py`, `files.lock.json`, optional side CSV (e.g. `bearings.csv`, `meta.csv`).
- `examples/private_datasets/my_cwru/`: private-dataset example (four CWRU files, `local` source).
- `tests/`: `test_build.py` (toy dataset in `conftest.py`, README sync tests),
  `test_sources.py` (local HTTP servers, mocked APIs).

## Adding or changing a dataset

Follow `CONTRIBUTING.md`. Things that matter in practice:

1. **Read the record and the paper first.** Before writing the builder, stage the raw files
   and inspect them. When the files disagree with the documentation (sampling rate, counts,
   durations, labels), trust the files and say so in `description`.
2. `builder.py` defines `CHANNELS` (per-channel `sensor_location`, `quantity`, `axis`,
   `unit`, `fs`) and `recordings(raw_dir)`, a generator of dicts with `recording_id`,
   `native_label`, `condition`, `fault_location`, optional columns, optional per-recording
   `fs`, and `signals`. Any value can be a `{channel: value}` dict covering every channel
   (per-channel `fs`, or `bpfo` of the bearing each sensor is on). Its module docstring
   describes the raw file layout. Match the style of existing builders.
3. Schema rules (enforced by `validate()`):
   - `condition` uses only `CONDITIONS` words, joined with `+` in vocabulary order
     (`inner+ball`); `fault_location` is `none` when healthy.
   - No nulls: use `none` (does not apply) or `unknown` (not documented). A column must
     apply to every row; otherwise leave it out.
   - Every non-standard column is described under `columns:` in `dataset.yaml`. Prefer the
     standard `OPTIONAL` names (`rpm`, `load`/`load_unit`, `severity`, `fault_size_mm`,
     `speed_profile`, `run_id`/`time_s`/`rul_s`, ...) over new ones.
   - Keep signals in their original dtype and values (no resampling or normalisation).
4. Verify a build: recording count, `n_samples`/`fs` per channel, label balance, a few
   signal values, against the record and paper. Update `size:` with the measured sizes.
5. Update `README.md`, which tests check: the dataset row in the right group, the group count,
   the headline "**N public**", the "**N datasets**" line, and the dataset-specific
   columns table. Also update the standard-columns table (not tested) and, if useful, a
   note in `docs/guide.md` §6.
6. A half-finished dataset folder makes the README tests fail. Move it out of
   `src/bearing_datasets/datasets/` before running the full suite and committing.
7. One commit per dataset; commit `dataset.yaml`, `builder.py`, `files.lock.json` and side
   CSVs. Never commit data.

Skip a dataset rather than add it when: labels cannot be mapped, the data is not raw
waveforms (features, images, SCADA tables, videos), the format is proprietary, or it cannot
be downloaded without a login. Record it in the "Evaluated and not included" table of
`docs/diversity.md`.

## Code conventions

- Ruff, line length 100, Python >= 3.10. Match the surrounding comment density and idiom.
- Always pass `encoding="utf-8"` to text I/O (`read_text`, `write_text`, `open`): on Windows
  the default is cp1252, and dataset YAMLs contain non-ASCII text. A test runs the CLI with
  `-X warn_default_encoding` to catch this.
- Do not assume symlinks work (Windows without admin rights): use `build._link()`.
- pandas 3 reads text columns as the `str` dtype, not `object`: test with
  `pd.api.types.is_numeric_dtype`, not `dtype == object`.
- Some hosts (e.g. Mendeley Data) reject the `requests` library: HTTP goes through the
  standard `urllib` in `sources._open`.
- Zenodo record ids redirect to the latest version: use the latest id in `dataset.yaml`.
- Kaggle public datasets download anonymously; some single files come wrapped in a zip and
  are unwrapped by `_unwrap_kaggle`. Kaggle competitions need a login (out of scope).
- Add a test for every core change (`tests/test_sources.py`, `tests/test_build.py`).

## Working on a shared server

- Disk is often shared: check free space before large downloads or builds, and stop before
  filling it (warn the user when it runs low).
- Build and experiment in a scratch root, not in the shared datasets folder, unless asked.
  Clean scratch builds after verifying them.
- Never delete or edit files you did not create (existing data folders, user files).
  Private datasets' raw files are only ever read (they are copied into the cache).
- Do not push, publish or change the user's saved root without being asked.
