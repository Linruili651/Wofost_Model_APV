# Hao Interface and Rerun-Hao

## Nitrogen extension added 2026-10-20-

Use `02_WLP_Model/Nitrogen_Extension/README.md` for the implemented WOFOST81/SNOMIN entry. Six sourced reference nitrogen runs and matching PP81/WLP81 checks completed (18 total); all six Aachen field checks explicitly stop on missing inputs. Historical WOFOST73 PP/WLP still have no soil-N cycling.

No real full-season APV–water–nitrogen coupling is claimed. Hao's current experimental scope remains four PV cases as previously confirmed.


- `Hao_Interface.py`: real WOFOST crop interface.
- `Rerun_Models.py`: rerun either or both models.
- `Model_Overview.ipynb`: crop/model overview.
- `Y_Usage_Guide.ipynb`: local and Colab workflow.
- `Shared_Core/`: shared crop engine, weather/grid utilities and module loader.
- `Shared_Inputs/`: six-crop catalog, official parameter snapshots and reference screenshot.
- `Rerun_Results/`: outputs and six-crop comparison.
- `Historical_Files/`: original RE/Y and old PP rainfall comparisons.
- `Validation/`: relocation checks, model tests and notebook checks.

## Python API-Python

Run from the package root.

```python
import runpy
api = runpy.run_path("06_Hao_Interface_and_Rerun/Hao_Interface.py")
result, folder = api["evaluate_crop_yield"](
    crop_id="potato", mode="WLP_MLWB",
    accept_demo_assumptions=True, return_details=True)
```

`yield_kg_DM_ha` is storage-organ dry matter, not fresh yield. Incomplete grain seasons are not replaced with zero.

APV inputs must cover every day and point with `day,scenario_id,point_id,x_m,y_m,cell_area_m2,total_Wh_m2_day`. Optional `effective_rain_mm_day` requires an explicit source.

The original RE used radiation sum × 1.25 as a placeholder. Use the new interface, not the archived original.
