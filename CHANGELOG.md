# Changelog

## 0.2.0

Column names and values follow one pattern, `<subject>_<attribute>[_<unit>]`, and the
categorical columns use fixed vocabularies, checked at build time. The location and mounting
words follow ISO 20816-1, ISO 13373-1, IEC 60034-7, ISO 14224 and ISO 5593.

Datasets built with 0.1 still open: their columns are renamed on read, with a warning.
Rebuild them (`bearing-datasets build <name> --force`) to get the new locations and columns.

### Renamed

| 0.1 | 0.2 |
|---|---|
| `condition` | `fault_type` ("condition" was ambiguous: fault or operating condition) |
| `fault_type` value `ball` | `rolling_element` (also roller and needle bearings) |
| `rpm` | `speed_rpm` |
| `severity` | `fault_severity` |
| `build(where={"condition": ...})`, `--where condition=...` | `fault_type` (the old name still works, with a warning, until 0.3) |

### New columns

* `sensor_at_fault` (every dataset): True when the sensor is at a faulty position, computed
  from `sensor_location` and `fault_location`. `unknown` positions are never at the fault, and
  `motor_supply` (currents, voltages) only matches a `motor_supply` fault.
* `sensor_mounting`: the surface the sensor is on: `pedestal`, `casing`, `outer_ring`,
  `shaft`, `base`, `none`, `unknown`.
* `fault_severity_level`: 0 healthy, then 1, 2, … from the mildest, within a dataset and
  fault type; 1 for a fault the dataset does not grade (`fault_severity="not graded"`).
* `operating_condition` (now standard), `speed_setpoint_rpm`, `bearing_model` (now standard),
  `repetition` (now standard).

### Changed values

* `sensor_location` and `fault_location` use one vocabulary (`LOCATIONS` in `schema.py`):
  `<unit>_<item>[_<position>]`, e.g. `motor_bearing_de`, `gearbox_bearing_input`,
  `test_bearing`, `support_bearing_nde`, `motor_supply`. The surface (housing, outer ring) moved
  to `sensor_mounting`. Examples: CWRU `bearing_de` / `bearing_fe` are now `motor_bearing_de` /
  `motor_bearing_nde`; `test_bearing_housing` is `test_bearing` with `sensor_mounting=pedestal`.
* `validate()` checks the vocabularies of `fault_type`, `fault_location`, `sensor_location`,
  `sensor_mounting`, `quantity`, `axis`, `speed_profile` and `fault_origin`, and that
  `fault_location` is `none` exactly for `normal` and has one part per `fault_type` part (or is
  `unknown`).
* `build(where=...)` raises an error for a column that is not set per recording (e.g.
  `sensor_location`), instead of keeping nothing.
* `speed_profile` gains `varying` (speed changes, shape not documented) and `unknown`.

### Dataset-specific columns folded into standard ones

* `operating_condition` ← bjtu_bogie `working_condition`, cumtb_pitch and mehran_uet
  `load_condition`, haust_ldv `load_case`; new in paderborn, phm09, seu, tecnalia_bearing.
* `speed_setpoint_rpm` ← phm09 and seu `speed_hz` (x 60), saarland `speed_target_rpm`,
  hse_similar_system `speed_set_rpm`, mcc5_thu_* `rpm_setting`; estogu's nominal speed.
* `repetition` ← arkansas, ottawa_2018 and vit_taper `trial`, phm09 `repeat`, laspi
  `acquisition`, nln_emp `sample`.
* `load` / `load_unit` ← haust_ldv `radial_load_n`, mcc5_thu_* `torque_setting_nm`;
  mcc5_thu_* `varying` → `speed_profile`.
* `fault_detail` ← cumtb_pitch `fault_type`, uoemd and vit_taper `fault`.
* Removed (redundant): bjtu_bogie `motor_speed_hz` and `sensor_position`, tecnalia_bearing
  `shaft_hz`. Renamed: im_vacd `mounting` → `phone_mounting`, saarland `sensor_mounting` →
  `sensor_mounting_deviation`, uoemd `load_condition` → `load_state`.

### Migrating a private dataset

A builder written for 0.1 fails to build with 0.2 (missing `fault_type`, unknown values). In
its `recordings()` and `CHANNELS`:

* yield `fault_type` instead of `condition`, `speed_rpm` instead of `rpm`, `fault_severity`
  instead of `severity`; write `rolling_element` instead of `ball`;
* use the `LOCATIONS` of `schema.py` for `sensor_location` and `fault_location` (e.g.
  `bearing_de` → `motor_bearing_de`, `test_bearing_housing` → `test_bearing`), and put the
  surface in `sensor_mounting`;
* rename a column of your own that now has a standard name (`fault_type`, `repetition`,
  `operating_condition`, ...), or move its values into the standard column.

The build lists every remaining problem at once.

### Documentation

* README: two column tables (columns in every dataset; columns in some datasets, with the
  datasets that have each), the location vocabulary, and an example of the sensor columns of
  two datasets.
