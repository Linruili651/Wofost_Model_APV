# Three Radiation Notebooks-

## Current Aachen calculation plan-(2026-10-19)

The user now plans all six combinations (two constructions × three mounting forms), each coupled to PP/WLP for six crops. The three code files contain both construction branches. This is the current calculation plan; the four-case scope described below refers to Hao's previously stated completed experimental scope. See `../Six_PV_Configurations_and_PP_WLP_Run_Plan.md` for the 72 PV comparisons plus 12 open-field baselines.

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

## Located originals-

The screenshot files were found under ``, with `(1)` added to their filenames. The copies in `Original_Notebooks` retain every original byte, including saved old outputs. See the source manifest for hashes.

|Notebook-|Purpose-|Original defaults-|
| --- | --- | --- |
|`fixed_tilt.ipynb`|Fixed tilt, azimuth, row pitch and clearance; compare semi-transparent and opaque constructions.|25° tilt, south facing, 3 m clearance; 2024-10-01 through 2024-10-02; both outputs on.|
|`vertical_pv.ipynb`|Tilt fixed at 90°, lower edge at ground level; front east/rear west by default.|2024-06-21; Hao on, ground off. / 621, Hao, .|
|`single_axis.ipynb`|Hourly single-axis rotation with angle limit and backtracking.|North–south axis, 3 m hub, ±45°, backtracking; 2024-03-01 through 2024-03-30; BOTH outputs off.|

## Inputs and outputs-

All three use the Aachen EPW weather, module dimensions and cell layout, glass optical assumptions, array size, row pitch and geometry. Each compares two constructions: physical opaque cells with transmitting glass/gaps, and a conventional opaque module.

- **Hao:** four hourly array-integrated incident-energy columns (front/rear × two constructions), unit **Wh per hour interval for the whole array**. Rear results already include each construction's bifaciality. These are inputs for energy calculations; electrical conversion, inverter efficiency and losses are absent.
- **Linrui:** six ground energy totals (direct/diffuse/total × two constructions), unit **Wh integrated over the selected land and whole selected period**, one row per run. They are neither daily W/m² nor ready-to-use WOFOST daily MJ/m². Divide by the correct land area, aggregate each day and convert units before crop coupling; a whole-season total alone cannot recover the daily series.

`crop_name` is a record label here. No crop growth, roots, soil water, precipitation redistribution or nitrogen leaching is simulated in these notebooks. Those belong to the crop/soil modules.

## Execution scope-

The run copies explicitly select 2024-06-21 12:00–13:00 in EPW local standard time, 2×2 modules, a 4×4 ground grid, two workers and low accuracy, with BOTH outputs enabled. Cell count, module dimensions, glass, rear weighting and each model's default installation geometry remain unchanged.

These are short numerical execution checks, not the original full-period default runs, a full growing season, parameter calibration or a complete APV–WOFOST coupling. The executed copies contain their explicit override cell. See `Execution_Summary.md` and per-model logs for actual pass/failure status.

## Rerun environment-

Use a separate Python environment for radiation dependencies. Radiance command-line tools (`rtrace`, `oconv`, `genbox`, `xform`, `gendaylit`) and the Radiance `lib` directory must also be available through PATH and RAYPATH.

Official sources

Keep the older notebooks and adapters in the parent folder for provenance. The older daily bridge was not verified against these three newer hourly/period schemas; this handoff does not silently substitute one for the other.

From this three-model folder, install the recorded dependencies and run the portable launcher. It checks all three models by default, creates a new timestamped folder and preserves prior outputs. The launcher sets weather/output paths; the original notebook's `weather/` layout need not be created.

```powershell
python -m pip install -r "Tested_Requirements.txt"
python "Run_Three_Models.py" --radiance-home "C:/Radiance"
```

If PATH and RAYPATH are configured, omit `--radiance-home`. To run just one, add `--model fixed_tilt`, `--model vertical_pv` or `--model single_axis`.
