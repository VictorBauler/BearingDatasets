# Physical-bearing diversity of the datasets

How many **distinct physical bearings** each dataset contains, and whether an evaluation can
keep a bearing out of training (*leave-bearing-out*). Recordings of one bearing under many
speeds and loads look alike, so with one bearing per class a model can learn to recognise the
bearing instead of the fault, and a random split of the recordings gives optimistic results
([Vieira et al., 2026](https://doi.org/10.1016/j.ymssp.2026.114640)).

The datasets are grouped by whether leave-bearing-out evaluation is possible, most diverse
first within each group. The counts come from the downloaded files and the builders (file
names, folders, metadata tables) and from the dataset notes in [the guide](guide.md). They are
**a judgment, not a measurement**: **?** marks what the files and documents do not confirm
(typically, whether each class used a different physical bearing).

If you know a dataset better (e.g. you are one of its authors), please open an issue: we will
correct it.

**In the package:** `bearing_id` identifies the physical bearing in cwru, ferrara_or,
hit_intershaft, hse_similar_system, hust, hustbearing, ottawa_uored, paderborn and saarland;
split by it (e.g. scikit-learn's `GroupKFold`). In run-to-failure datasets, `run_id` plays the
same role (one run = one bearing, or one set of bearings).

## Leave-bearing-out possible (9)

Several documented physical bearings per class (bearing ids or runs).

| Dataset | Task | Distinct bearings | Notes |
|---|---|---|---|
| `paderborn` | diagnosis | 32 | 6 healthy, 12 artificial and 14 real (accelerated-life) damaged 6203 bearings, `bearing_id` per bearing, several bearings per class: the reference for leave-bearing-out and artificial-to-real transfer. |
| `ottawa_uored` | diagnosis | 20 | 5 bearings per class (inner, outer, ball, cage), each also recorded healthy (stage 0) and at two fault stages: every bearing is its own healthy reference. |
| `paderborn_rtf` | prognostics | 17 | 17 new bearings run to failure (B01-B17) under random speed and load, natural damage (defects found after dismantling). Sampling rate changes at B10. |
| `hust` | diagnosis | 33 (>= 4 per class) | 33 fault x bearing-type combinations x 3 loads = 99 recordings. Every fault class is on 5 bearing models (6204-6208; ball and inner+ball have no 6204), so each class has at least 4-5 distinct physical bearings: leave-one-bearing-type-out is possible. The total of 33 assumes each combination is its own bearing (?): the record does not say whether one bearing of a model was damaged in steps (e.g. inner, then inner+outer). |
| `femto` | prognostics | 17 | 17 run-to-failure bearings, 3 conditions; no fault-type labels. |
| `xjtu_sy` | prognostics | 15 | 15 bearings to failure, 5 per condition; failed elements known per run, but most failure modes have 1-3 bearings. |
| `saarland` | diagnosis | 3 | 3 cylindrical roller bearings, each measured undamaged and then damaged, under a designed experiment (speed, load, mounting, worker): built for domain shift; leave-one-bearing-out possible. |
| `ferrara_or` | diagnosis | 9 | The files confirm 3 different bearings (a, b, c) per defect width, `bearing_id` in the package. No healthy bearing, outer race only. |
| `unsw` | prognostics | 4 | 4 run-to-failure tests with naturally growing spalls, encoder and load signals; best for severity tracking. |

## Partly possible (27)

Some bearing-level diversity (several bearings, bearing types, runs or real damage), but not enough, or not documented enough, to leave a bearing out of every class.

| Dataset | Task | Distinct bearings | Notes |
|---|---|---|---|
| `cwru` | diagnosis | 21 (1 healthy) | Each fault size at each end (DE, FE) is its own seeded bearing: 7 inner, 7 ball and 6 outer race bearings, so the fault classes allow leave-bearing-out (`bearing_id`). But every normal recording comes from the same healthy bearing, so the healthy class cannot be left out. Outer race faults at 3, 6 and 12 o'clock are counted as one bearing, since CWRU does not say whether they are different bearings; `bearing_id` also assumes the 4 loads of a fault used the same bearing (?). |
| `sca` | anomaly | 10+ | Real machines of a paper mill, faults developed in operation on many different industrial bearings (11 cases). Labels per measurement; case 11 is labelled normal although described as misalignment. |
| `dlr_needle` | prognostics | 16 | 8 run-to-failure tests x 2 needle bearings, varying lubrication and load; which of the two bearings failed is not stated. |
| `hse_similar_system` | diagnosis | 15? | 4 bearing types on 2 rigs (cylindrical and needle, plastic and metal cage). `bearing_id` assumes one physical bearing per model, cage and fault, shared by both rigs. |
| `ferrara_rtf` | prognostics | 6 | 6 bearings run to failure, all ending with an extended outer raceway defect; per-snapshot condition unknown. |
| `uos` | diagnosis | 12? | 3 bearing types (ball, cylindrical, tapered) x 4 bearing conditions, crossed with rotor faults. Probably one bearing per condition and type. |
| `bjtu_bogie` | diagnosis | 17? | Motor, gearbox and both axle-box bearings with 4 fault types each (different bearing positions and sizes); one bearing per fault state. |
| `ims` | prognostics | 12 | 3 tests x 4 bearings; 4 documented failures (inner, roller, outer x2), natural damage. |
| `mehran_uet` | diagnosis | 13? | 6 inner and 6 outer race fault sizes (0.7-1.7 mm), presumably one bearing each, plus healthy. |
| `cumtb_pitch` | diagnosis | 12? | 12 states of a scaled pitch bearing (crack, spalling, wear, compound, gear-teeth root crack); one bearing per state. Very low speed. |
| `haust_ldv` | diagnosis | 10? | Healthy + 3 pitting sizes on inner, outer and roller; laser vibrometer (non-contact). One bearing per state. |
| `sdust` | diagnosis | 10? | 10 states (3 sizes x 3 locations + normal) under many speeds and loads; one bearing per state. |
| `nln_emp` | diagnosis | 10? | Industrial pump sets, motor bearing faults of 3 severities, rolling element, contaminated grease, pump bearing; several healthy references at different moments. |
| `dirg` | diagnosis | 7 | 7 aeronautical roller bearings (0A-6A: 3 indentation sizes on inner ring or roller); endurance run on 4A at 18000 rpm. |
| `lenze_mb` | diagnosis | 7? | 5 natural pitting levels + a heavy artificial damage + normal, drive signals only. Unclear whether the pitting levels are different bearings. |
| `dlr` | diagnosis | 7? | Healthy + 3 inner and 3 outer spall sizes on aerospace four-point-contact bearings; one bearing per size. |
| `kaist_load` | diagnosis | 7? | 3 inner and 3 outer fault sizes + normal on housing A, plus misalignment and unbalance levels; multi-sensor (vibration, current, temperature, acoustic). |
| `mcc5_thu_motor` | diagnosis | 7? | Motor bearing faults (inner/outer at 2 widths, ball pitting, inner + outer) among many motor faults, time-varying speed and load. |
| `hit_intershaft` | diagnosis | 4 | 4 inter-shaft bearings of a real dual-rotor aero-engine (healthy tested twice, 2 inner, 1 outer), `bearing_id` in the package. |
| `hit_sm` | diagnosis | 7? | Two rigs (SpectraQuest and self-built) with normal and inner/outer faults of 3 arcs; not clear whether both rigs used the same bearings. |
| `vibrobox` | diagnosis | 3? | Normal and outer ring fault bearings (one with an incipient inner defect) over many speed profiles; few bearings. |
| `hustbearing` | diagnosis | 9 | 9 states (2 severities x 4 fault types + healthy), one bearing each (`bearing_id`), constant and varying speed. |
| `mcc5_thu_gearbox` | diagnosis | 6? | Bearing faults (3 widths, inner/outer) only together with a broken tooth; mainly a gear dataset. |
| `army_pla` | diagnosis | 6? | NU205 cracks on inner, outer, roller, cage, inner + outer, and mixed with gear faults; one bearing per state. |
| `adelaide` | other | ? | Defect slope and defect length series on two bearing types; several machined defects, but how many physical bearings is not clear from the file prefixes. |
| `mfpt` | diagnosis | 3+ | Rig NICE bearing (baseline, outer, inner) plus 3 real-world bearings from other machines (wind turbine, oil pump, planet bearing). |
| `phm09` | diagnosis | ? | Gearbox with bearing faults (inner, ball, outer, combination) mixed with gear and shaft faults, several at once. |

## Unknown (2)

The files and documents do not say how many bearings were used.

| Dataset | Task | Distinct bearings | Notes |
|---|---|---|---|
| `uc204` | diagnosis | 5? | Healthy + 4 outer groove lengths; not stated whether the groove was lengthened on one bearing or made on 4. |
| `estogu` | diagnosis | 3? | Ball and ring defects; the README says drilled, the setup text says worn industrial bearings (origin unknown). |

## One bearing per class (31)

One bearing (or one machine) per class: a random split of the recordings tends to overestimate accuracy (see [Recommendations](#recommendations)).

| Dataset | Task | Distinct bearings | Notes |
|---|---|---|---|
| `neepu` | diagnosis | 7 | One bearing per state (single and compound), 4 loads. |
| `seu` | diagnosis | 5 | One bearing per class, 2 conditions; truncated files. |
| `ottawa_2018` | diagnosis | 5 | One bearing per class under 4 speed profiles. |
| `isac` | diagnosis | 3? | Outer or ball fault moved between 3 positions; probably the same faulty bearings. |
| `vit_sq` | diagnosis | 7 | One bearing per state (single and combined). |
| `vit_taper` | diagnosis | 5 | One tapered bearing per state. |
| `hust_transmission` | diagnosis | 2 | Left outer race and right inner race bearings among many transmission faults. |
| `laspi` | diagnosis | 3 | Supplied faulty components: one inner and one outer race bearing. |
| `subf_v1` | diagnosis | 3 | One bearing per class, 6 h each cut into 10 s segments (segments of one run look alike). |
| `subf_v2` | diagnosis | 3 | Same as subf_v1, microphone. |
| `dcase_bearing` | anomaly | ? | One machine; anomalies not labelled per clip. |
| `tecnalia_gearbox` | diagnosis | 1 | One outer race fault bearing (plus broken tooth). |
| `tecnalia_bearing` | diagnosis | 1 | One outer race fault bearing, 4 tests. |
| `uaq_upc` | diagnosis | 1 | One drilled outer race bearing among motor and gear faults; vibration on the gearbox. |
| `arkansas` | diagnosis | 2 positions | Faults in two bearing positions, single and double; one bearing per fault type and position. |
| `just_slewing` | diagnosis | 4 | Large slewing bearing, one per state, very low speed. |
| `sqv` | diagnosis | 7 | One bearing per state, hand-controlled run-ups. |
| `fstf` | diagnosis | 6 | Gunt PT 500 kit bearings, smartphone sound. |
| `susu` | diagnosis | 5 | 5 test bearings, one per state; shaft-mounted wireless sensor. |
| `urma_crti` | diagnosis | 5 | One bearing per state. |
| `jnu` | diagnosis | 4 | One bearing per state, 12 recordings. |
| `kaist_speed` | diagnosis | 4 | One bearing per state; fault location unknown in the constant-speed files. |
| `uestc` | diagnosis | 4 | One bearing per state, 4 speeds. |
| `im_vacd` | diagnosis | 1 | Each fault on a different motor (motor confounded with class); one faulty bearing. |
| `kimm_pmsm` | diagnosis | 1 | One bearing fault module (balls removed) among motor faults. |
| `uoemd` | diagnosis | 1 | Each fault a different motor; one faulty bearing, defect not described. |
| `kaist_rtf` | prognostics | 1 | One bearing to failure. |
| `upm_citef` | diagnosis | ? | Railway axlebox bearings with milled defects at 4 depths per component; likely one bearing per depth. |
| `vbl_va001` | diagnosis | 1 | One pump per condition (machine confounded with class); one hammered bearing. |
| `wt_hss` | prognostics | 1 | One field wind-turbine bearing, inner race fault developing over 50 days. |
| `mafaulda` | diagnosis | 6? | Ball, cage and outer faults in 2 positions; one bearing per fault type and position. |

## Recommendations

- For **leave-bearing-out diagnosis**: `paderborn`, `ottawa_uored`, `hust`, `saarland`,
  `ferrara_or` (outer race severity), and `cwru` for the fault classes (its healthy class has one
  bearing). Group splits by `bearing_id`.
- For **prognostics**: `paderborn_rtf`, `femto`, `xjtu_sy`, `dlr_needle`, `ferrara_rtf`,
  `ims`, `unsw`. Group by `run_id`.
- For **real (non-seeded) damage**: `paderborn` (14 bearings), `sca`, `mfpt` (field
  recordings), `wt_hss`, and the run-to-failure sets.
- Datasets with one bearing per class are still useful for pre-training, robustness (speed,
  load, sensors) and cross-dataset tests, but a random split of their recordings measures how
  similar the recordings are more than how well faults are recognised.

## Evaluated and not included

| Dataset | Reason |
|---|---|
| IFSP bronze bushings | plain (sliding) bearings, not rolling bearings |
| MOIRA | proprietary TwinCAT `.svdx` files (174 GB) |
| NOVIC+ | only pre-split `.npy` arrays, not the raw recordings (82 GB) |
| HDU | hosted on Baidu, needs a login |
| GUET | proprietary `.bkc` files |
| VIT Vishwakarma | mixed acquisitions, duplicated files, unreadable MATLAB table files |
| NUST journal bearings | RMS and kurtosis trends and reports, no raw waveforms |
| Luleå | no fault labels |
| SDOL | two unlabelled example signals |
| CARE to Compare, Siemens | SCADA tables, not waveforms |
| EJUST | videos, not waveforms |
| IEEE DataPort sets | need a login |

Also evaluated: AITHE, ISED, Fraunhofer LBF and the Selçuk radar set. A dataset can be
reconsidered when its files change: see [CONTRIBUTING.md](../CONTRIBUTING.md).

## References

Vieira, J. P., Bauler, V. A., Rosa, R. K., & Silva, D. (2026). Towards a more realistic
evaluation of machine learning models for bearing fault diagnosis. *Mechanical Systems and
Signal Processing*, 258, 114640. https://doi.org/10.1016/j.ymssp.2026.114640
