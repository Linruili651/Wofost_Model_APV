# Nitrogen Extension Handoff-

Updated

## Delivered behavior-

The new `NWLP_MLWB_SNOMIN` entry couples WOFOST 8.1, multilayer soil water and SNOMIN soil carbon/nitrogen. It calculates layer NH4/NO3 stocks, crop soil-N uptake, biological fixation, mineralisation/nitrification/denitrification and soil-water-driven N transport.

**Six reference nitrogen runs succeeded; six Aachen field cases are blocked by explicitly listed missing inputs. This is not six calibrated Aachen nitrogen-leaching estimates.** / **; Aachen, Aachen. **

The historical WOFOST7.3 PP/WLP entries and results remain available. Matching WOFOST8.1 `PP81` and `WLP81` reference checks were also run: six crops × three modes = 18 new reference runs. Use version-matched comparisons; an old 7.3 yield minus a new 8.1 yield does not isolate nitrogen effects.

## Inputs and their evidence-

|Input-|Evidence-Treatment|
| --- | --- |
|Six crop parameter sets-|Downloaded the official WOFOST81 branch at a fixed commit; kept the existing six variety IDs. Full original YAML, URLs and SHA-256 are included. Generic source parameters, not local calibration.|
|Soil organic matter, pH, C:N, initial NH4/NO3-, pH,|Official PCSE notebook 12 provides a complete Dutch demonstration profile: 25/15/20/60 cm, total 120 cm, with sourced values. Used only in the explicitly enabled technical reference.|
|SNOMIN reaction parameters-|Published notebook values and the exact installed PCSE6.0.13 site-provider source are archived. They are model references, not measured Aachen rate constants.|
|Regional mineral N-NRW|Archived NRW 2026 winter/summer Nmin pages. They provide regional seasonal mineral-N totals; they do not supply the required field/date/species-specific full-profile initial conditions.|
|Fertilization-|Field records remain null. The reference is an explicitly unfertilised technical control ([]), not an unknown field filled with zero. A separate software check uses the official potato May-1 event, 85 kg N/ha, relabelled to the synthetic year.|
|Aachen initial N and organic/pH profile-Aachen|Remain null pending actual plot confirmation, dated soil observations and sourced management. The old WLP FSOMI=0/C:N=10/pH=6.5 placeholders are explicitly removed from the new field template.|

`Aachen_Field_Inputs.json` is the strict default. Both values and `field_sources` must be completed, and resolved items removed from `missing_parameters`; unknowns stop execution. `Published_Reference.json` is separate and requires an explicit flag. No reference N values were copied into the Aachen field template.

**Reference choices:** retained the published 400ppm CO2 and rain NH4-N=1/NO3-N=4 mgN/L; these are source-example values, not current atmosphere/local deposition. NOTINF uses the documented PCSE default 0 for this rain-fed control instead of the drip-irrigated example's 1. This change and its source are recorded in JSON.

## Nitrogen boundary audit-

`nitrogen_leaching_kg_N_ha` = nitrate-N + ammonium-N crossing the bottom of the entire simulated soil profile. The reference boundary is **120cm**, not the crop's changing root depth and not the older BK50 200cm boundary.

Inspection of PCSE6.0.13 shows its native `NO3LEACHCUM`/`NH4LEACHCUM` accumulate `RNO3OUT[-1]`/`RNH4OUT[-1]`; those layer-outflow arrays can include upward movement into the layer above. This extension audits actual rate components before integration, subtracts that internal upward component from the reported profile-bottom leaching and retains native counters under `pcse_native_*`. No installed PCSE equations are modified.

The bundled source also exports N at a negative top water-flow boundary. This is recorded separately as `pcse_native_top_boundary_N_export_kg_N_ha` so the N budget closes; it is a model-accounting term, not a validated estimate of runoff N or ammonia volatilisation. Native `NLOSSCUM` is preserved as `model_N_loss_kg_N_ha`; it is not a complete environmental N-loss total.

Each result includes daily crop/N summaries, layer NH4/NO3 in **kg N/ha per layer**, water flows, cumulative profile leaching, crop soil-N uptake, and fixation. Soybean retains the sourced `NFIX_FR=0.8`; biological fixation is not counted as soil N loss.

Daily rows follow PCSE state timestamps; a cumulative increment is the integrated preceding timestep. These simulations stop at crop maturity/termination. Winter wheat crosses autumn/winter, while spring crops have shorter exposure; the totals are not annual leaching and cannot be compared without matching the accounting window. Continuing after harvest/crop rotation is a later extension.

## Run from package root-

Use the crop environment (PCSE6.0.13), separately from the radiation environment.

```powershell
python -m pip install -r "06_Hao_Interface_and_Rerun/Requirements.txt"
python "02_WLP_Model/Nitrogen_Extension/Run_Nitrogen.py" --crop all --check-only --accept-demo-assumptions
```

The strict command currently reports six blocked cases and returns a nonzero code. That is the intended missing-data behavior; it has not calculated six zeros.

To reproduce the sourced technical checks only

```powershell
python "02_WLP_Model/Nitrogen_Extension/Run_Nitrogen.py" --crop all --mode all --nitrogen-inputs "04_Soil_and_Python/Nitrogen_Inputs/Published_Reference.json" --accept-reference-scenario --accept-demo-assumptions
```

`--mode NWLP_MLWB_SNOMIN` runs only the six water/N cases; `--mode all` runs all 18 version-matched checks. New run folders are created, preserving existing detailed results; the latest overview is refreshed.

Hao can load `Hao_Interface.py` and call `evaluate_crop_water_nitrogen(...)` for the payload and output folder. A radiation DataFrame must cover every daily point; `effective_rain_mm_day` supplies explicitly defined local rain. The existing three Tianze hourly/period radiation files are not automatically full-season daily crop inputs. / Hao; , effective_rain_mm_day. /.

Reference payloads have `scenario_kind=reference_only` and `eligible_for_field_optimization=false`. The scalar yield optimizer rejects them; request detailed outputs for technical evaluation.

## Official sources-

- [PCSE SNOMIN source and model citation](https://pcse.readthedocs.io/en/stable/_modules/pcse/soil/snomin.html)
- [Official SNOMIN example notebook](https://github.com/ajwdewit/pcse_notebooks/blob/master/12%20Simulating%20with%20WOFOST%208.1%20SNOMIN.ipynb)
- [Official WOFOST81 crop branch](https://github.com/ajwdewit/WOFOST_crop_parameters/tree/wofost81)
- [NRW Nmin references](https://www.landwirtschaftskammer.de/landwirtschaft/ackerbau/duengung/basisinfos/nmin/index.htm)

Frozen source commits, original files and hashes are in the nitrogen inputs' `Source_Manifest.json`.
