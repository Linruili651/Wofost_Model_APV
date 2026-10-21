# Handoff Guide-

## Nitrogen extension added 2026-10-20-

Use `02_WLP_Model/Nitrogen_Extension/README.md` for the implemented WOFOST81/SNOMIN entry. Six sourced reference nitrogen runs and matching PP81/WLP81 checks completed (18 total); all six Aachen field checks explicitly stop on missing inputs. Historical WOFOST73 PP/WLP still have no soil-N cycling. / WOFOST81/SNOMIN, PP81/WLP8118; Aachen. WOFOST73PP/WLP. , . 

No real full-season APV–water–nitrogen coupling is claimed. Hao's current experimental scope remains four PV cases as previously confirmed. / Completed; Hao. 

## Folder map-

| Folder- | Contents- |
| --- | --- |
| `01_PP_Model` | PP entry scripts and notebook. / PP , .  |
| `02_WLP_Model` | Layered water-limited entry scripts and notebook. / , .  |
| `03_Precipitation` | Aachen weather, precipitation supplement, original ERA5 response and rain adapter. / Aachen , ,  ERA5 .  |
| `04_Soil_and_Python` | Official BK50 archive, soil profiles, extraction and hydraulic Python tools. / BK50 , ,  Python .  |
| `05_Tianze_Files` | Tianze originals, Python adapters and radiation configuration. / Tianze , Python , .  |
| `06_Hao_Interface_and_Rerun` | Hao API, rerun entry, shared crop engine/parameters, results and historical records. / Hao , , , .  |

The six folders form one package. Move or share them together. / , . 

## Quick start-

Install dependencies from the package root. / . 

```powershell
python -m pip install -r "06_Hao_Interface_and_Rerun/Requirements.txt"
python -m jupyterlab
```

Open one of these notebooks. / . 

- `01_PP_Model/Run_PP.ipynb`
- `02_WLP_Model/Run_WLP.ipynb`
- `06_Hao_Interface_and_Rerun/Model_Overview.ipynb`

Read the assumptions before setting `ACCEPT_DEMO_ASSUMPTIONS=True`. / , . 

```powershell
python "01_PP_Model/Run_PP.py" --crop all --accept-demo-assumptions
python "02_WLP_Model/Run_WLP.py" --crop all --accept-demo-assumptions
python "06_Hao_Interface_and_Rerun/Rerun_Models.py" --mode both --crop all --accept-demo-assumptions
```

## Crops and models-

The six crops are winter wheat, spring barley, grain maize, potato, sugar beet and soybean. / Winter wheat, Spring barley, Grain maize, Potato, Sugar beetSoybean. 

Both entries use PCSE 6.0.13 and WOFOST 7.3. PP has no water stress; WLP uses the multilayer water balance. /  PCSE 6.0.13, WOFOST 7.3. PP ; WLP . 

The shared engine and crop parameters are stored once under the Hao folder. The model folders select their respective mode. /  Hao ; Mode. 

Crop seasons, prices and reference values from the supplied screenshot are retained in `Shared_Inputs/Crop_Catalog.json` under the Hao folder. Reference yield/LER values do not overwrite simulated results. / ,  Hao ,  LER . 

## Assumptions-

- Yields are storage-organ dry matter; fresh/marketable yield conversion is not supplied. / , . 
- The BK50 soil is an uncalibrated nearby demonstration profile, not a confirmed field. Hydraulic curves are estimates. / BK50 , , . 
- The precipitation is a synthetic TMY liquid-rain supplement. Snowmelt and panel runoff redistribution are absent. /  TMY , . 
- Historical WLP calculates water only; the new NWLP/SNOMIN extension calculates nitrogen with explicitly sourced inputs. / WLP; NWLP/SNOMIN. 
- Actual full-season Radiance/APV coupling has not been run here. /  Radiance . 

## Naming and original data-

A module loader supports imports from the preserved project modules.

Original BK50 ZIP contents, original notebook code and source URLs remain intact for provenance. Their original internal names are retained inside the official archive. Software-generated hidden caches keep their native technical names. / , BK50 ,  notebook  URL . . 

The earlier “water rerun results” are PP rainfall comparisons, not WLP. They are archived under the Hao folder. / “” PP ,  WLP,  Hao . 

See each folder's `README.md` for its files and commands. / . 

## Three Tianze notebooks-

The screenshot files are under `05_Tianze_Files/Three_Radiation_Notebooks`. See its execution summary for the short-run results and limits. / Fixed_tilt, Vertical_PV, Single_axis_tracking; . 

## APV experiment scope-

Hao's stated cases are fixed tilt × conventional/semi-transparent, single axis × conventional, and vertical × conventional: **four cases**. Two panel types × three mounting forms would give six cases in total. The short six-combination code checks in the Tianze folder do not establish six formal experiments by Hao. See `Experiment_Scope.md` in the three-notebook folder. / Hao, Fixed_tilt×/, ×, ×, ****. ×; Hao. . 
