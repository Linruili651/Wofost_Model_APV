# Execution Summary-

## Experiment scope confirmed by Hao-Hao

Panel type and mounting form are separate factors. Conventional means traditional opaque PV; semi-transparent is the other panel type. Fixed tilt, single-axis tracking and vertical PV are three mounting forms. Their full combination gives six cases.

|Mounting form-|Conventional-|Semi-transparent-|
| --- | --- | --- |
|Fixed tilt-Fixed_tilt|Within Hao's stated scope / Hao|Within Hao's stated scope / Hao|
|Single axis-Single_axis_tracking|Within Hao's stated scope / Hao|Outside Hao's stated scope / Hao|
|Vertical-|Within Hao's stated scope / Hao|Outside Hao's stated scope / Hao|

Hao's stated scope therefore contains **four cases**, with the two semi-transparent extensions excluded because of time constraints. This scope comes from the user's relay of Hao's explanation, not an independent audit of Hao's full experimental results.

The three notebooks stored here contain both construction branches. Codex's previous one-hour checks exercised all six combinations in these copies. Those checks establish short-run code execution only; they do not establish six completed formal experiments by Hao. Preserve these test records as technical evidence, and keep the two additional semi-transparent checks outside Hao's four-case experimental scope.

The existing six-crop × PP/WLP natural-light baseline (12 runs) is a separate crop-model check. It does not establish completion of these four APV cases coupled to the crop model.

All three models completed actual Radiance calculations, including both constructions, both PV faces and ground direct/diffuse/total results.

**Scope

|Model-|Status-|New outputs-|Time-|
| --- | --- | --- | --- |
|`fixed_tilt`|Passed|Hao: 1 hourly row, 4 energy columns; Linrui: 1 period row, 6 ground energy columns. / Hao14; Linrui16.|31.88 s|
|`vertical_pv`|Passed|Hao: 1 hourly row, 4 energy columns; Linrui: 1 period row, 6 ground energy columns. / Hao14; Linrui16.|23.26 s|
|`single_axis`|Passed|Hao: 1 hourly row, 4 energy columns; Linrui: 1 period row, 6 ground energy columns. / Hao14; Linrui16.|28.07 s|

## Numerical values-

All entries below are Wh integrated over the corresponding array or evaluation land, for this one-hour case. Different geometries have different evaluation footprints; do not interpret these land-integrated totals as area-normalized comparisons.

|Model-|Semi front-|Semi effective rear-|Opaque front-|Opaque effective rear-|Semi ground total-|Opaque ground total-|
| --- | --- | --- | --- | --- | --- | --- |
|Fixed_tilt|8648.963|1152.251|9367.461|1244.732|32214.448|32099.256|
|Vertical_PV|2481.280|1305.557|2682.054|1409.246|28564.972|27086.713|
|Single_axis_tracking|7820.693|1135.675|8469.585|1223.462|32811.302|32689.300|

The ground diffuse column is total minus the direct-only trace, so it includes scattered/reflected contributions.

## Evidence and limits-

- `Run_Results/`: each model has the actual executed notebook, two new CSVs, execution log and structured record. Original notebook saved outputs are not used as evidence for this run.
- Checks passed: unchanged source hashes; four finite positive PV energy values; six finite nonnegative ground values; direct + diffuse = total; one row per output; valid executed notebooks; tracker angle within ±45°. These are execution and internal-consistency checks, not experimental validation.
- No default full-period runs, full-season runs or crop/soil coupling were performed. This run does not validate soil layers, rooting depth, nitrogen loss, rain redistribution or electrical yield.
- `single_axis` has both outputs disabled by default, and `vertical_pv` has the ground output disabled. The explicit override cell enables them for this check.
- `Tested_Environment.json` and `Tested_Requirements.txt` record the separate Python 3.13.5 radiation environment and Radiance 6.0.2. The existing PCSE crop environment was left untouched.
