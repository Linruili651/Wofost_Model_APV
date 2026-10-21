# WLP Model-WLP

## Adaptive inputs


## Nitrogen extension added 2026-10-20-

Use `02_WLP_Model/Nitrogen_Extension/README.md` for the implemented WOFOST81/SNOMIN entry. Six sourced reference nitrogen runs and matching PP81/WLP81 checks completed (18 total); all six Aachen field checks explicitly stop on missing inputs. Historical WOFOST73 PP/WLP still have no soil-N cycling.

The active full-season scope is open field, fixed-tilt conventional PV and fixed-tilt semi-transparent PV. Tracking/vertical cases are excluded. The adaptive-input queue uses estimated/reference soil-N conditions and is not a field-validated nitrogen experiment.

Run `Run_WLP.ipynb` or `Run_WLP.py`.

The model is Wofost73_WLP_MLWB. Soil inputs come from `../04_Soil_and_Python/Soil_Inputs/`.

It calculates root uptake, layered storage/flow, evaporation, transpiration, runoff and bottom drainage. Nitrogen leaching is not included.

Results: `../06_Hao_Interface_and_Rerun/Rerun_Results/WLP_MLWB/`.

The demonstration soil and water curves require field review and calibration.
