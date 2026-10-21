- 03_Precipitation/Precipitation_Supplement.json: 365 , , , , .
- precipitation_adapter.py: ,  EPW , 365 , .
- Tianze_Crop_Hao_with_precipitation.ipynb: , .
-  Notebook, bridge.py  EPW ; .
- precipitation_sources/open_meteo_era5_fixed_UTCplus1_raw.json:  API , .

allow_missing_rain_for_pp  False, .


```python
from precipitation_adapter import attach_precipitation
weather, rainfall_info = attach_precipitation(
    weather, EPW, ROOT / 'inputs' / 'Aachen_TMY_precipitation_supplement.json',
    component='liquid_rain')
weather_info.update(rainfall_info)
```


rain_mm_day ,  mm/day,  RAIN_mm_day .
precipitation_mm_day ; snowfall_cm_day ,  cm/day.
