# Previous Methodology-

Original methodology record; old paths are retained for provenance. Use the current root guide for commands.



```text
Tianze_Crop_Hao_Jupyter/
├─ 00_Handoff_Guide.md                 
├─ Tianze_Crop_Hao.ipynb          
├─ 01_PP/PP.ipynb            
├─ 02_WLP_MLWB/.ipynb 
├─ RE.py                         Hao 
├─ Y.ipynb                        Colab 
├─ inputs/                       , , 
├─ BK50/                         , 
├─ examples/                     
└─ _/              RE.py, Y.ipynb  PP 
```


1. Extracted,  `Tianze_Crop_Hao_Jupyter` .
2.  `python -m pip install -r requirements.txt`,  `python -m jupyterlab`.  Python 3.11/3.12 , PCSE  6.0.13.
3. ,  notebook. ,  `ACCEPT_DEMO_ASSUMPTIONS`  `True`.
4. `Y.ipynb` /Colab ;  `Tianze_Crop_Hao.ipynb` .


```powershell
python run_models.py --mode both --crop all --accept-demo-assumptions
python run_models.py --mode PP --crop potato --accept-demo-assumptions
python run_models.py --mode WLP_MLWB --crop winter_wheat --accept-demo-assumptions
```


|||||
| --- | --- | --- | --- |
|PP|`Wofost73_PP`|, PP ; /||
||`Wofost73_WLP_MLWB`|, , /, , ;||




|crop_id|||||
| --- | --- | --- | --- | --- |
|`winter_wheat`|Winter wheat|10-15  08-31|Winter_wheat_103||
|`spring_barley`|Spring barley|03-26  08-31|Spring_barley_301||
|`grain_maize`|Grain maize|05-01  10-31|Grain_maize_201||
|`potato`|Potato|04-15  09-30|Potato_701||
|`sugar_beet`|Sugar beet|04-05  10-22|Sugarbeet_601||
|`soybean`|Soybean|04-28  10-15|Soybean_901||






`BK50/ISBK50_EPSG25832_GeoPackage.zip`  Aachen , ,  SHA-256 . . , ONP , JDM  KRZ .


`bk50_adapter.py`  ONP  FK/NFK/LK(mm/dm) KF(cm/d), , /.  BK50 , . `soil_profile_demo.json` , .








## Hao


```python
from RE import evaluate_crop_yield

value = evaluate_crop_yield(
    crop_id="potato", mode="PP", accept_demo_assumptions=True)

payload, folder = evaluate_crop_yield(
    crop_id="potato", mode="WLP_MLWB", accept_demo_assumptions=True,
    return_details=True)
```



```text
day,scenario_id,point_id,x_m,y_m,cell_area_m2,total_Wh_m2_day
```


```python
from RE import evaluate_crop_yield
from crop_engine import GroundGrid

payload, folder = evaluate_crop_yield(
    "actual_full_season_radiation.csv",
    crop_id="winter_wheat", mode="WLP_MLWB",
    scenario_id="fixed_conventional",
    provenance={"source": "Tianze actual complete-season run", "run_id": "replace_with_real_id"},
    grid=GroundGrid(), accept_demo_assumptions=True, return_details=True)
```


`radiation_bridge.py`, `tianze_fixed.py`, `tianze_tracking.py`  Tianze . `01_PP`  `02_WLP_MLWB` .  Radiance ,  APV .


- `Hao_crop_yield.json`: , Mode, , , . , “”.
- `point_summary.csv`, `crop_daily.csv`: .
- `soil_layers_daily.csv`:  WLP , , .
- `actual_model_weather.csv`: .
- `config_and_parameters.json`: , , .

`yield_kg_DM_ha` ; , . `storage_organ_DM_kg_ha` , . `relative_yield_to_natural` , Mode, , .






- PCSE : https://pcse.readthedocs.io/en/stable/available_models.html
- : `inputs/crops_wofost73/SOURCE.json`, commit `3612078ae36a949a35b8712cc6deddf279b7fe81`, EUPL .
- BK50: https://www.opengeodata.nrw.de/produkte/geologie/boden/BK/ISBK50/ , GD NRW, dl-de/by-2-0. 
- : https://escomp.github.io/CTSM/release-clm5.0/tech_note/Hydrology/CLM50_Tech_Note_Hydrology.html , ,  CLM.
- : Open-Meteo  API / ERA5,  `inputs/precipitation_sources/`, CC BY 4.0.
