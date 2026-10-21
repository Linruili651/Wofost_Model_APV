```python
hao_hourly, ground_summary = model_for_optimization(
    candidate_design, scenario, module_specification, array_specification,
    calculate_linrui=True,  # ,  Linrui 
    calculate_hao=False,    # , 
)

ordinary_ground_energy = ground_summary["conventional"]["ground_total_incident_energy_Wh_period"]
semi_ground_energy = ground_summary["semi_transparent"]["ground_total_incident_energy_Wh_period"]
```

`hao_hourly`  `ground_summary` , . / `ground_summary` .  total , ,  Wh, .



`save_selected_results(...)` :

||CSV|
| --- | --- |
|,|`conventional_ground_direct_incident_energy_Wh_period`|
|,|`conventional_ground_diffuse_incident_energy_Wh_period`|
|,|`conventional_ground_total_incident_energy_Wh_period`|
|,|`semi_transparent_ground_direct_incident_energy_Wh_period`|
|,|`semi_transparent_ground_diffuse_incident_energy_Wh_period`|
|,|`semi_transparent_ground_total_incident_energy_Wh_period`|



||||
| --- | --- | --- |
|Fixed_tilt|`Linrui_fixed_tilt_scenarios.csv`|＋|
|Single_axis_tracking|`Linrui_single_axis_scenarios.csv`|＋;|
||`Linrui_vertical_pv_scenarios.csv`|＋;|


CSV  scenario_name, run_id, period_start, period_end, weather_filename, , , . , .



`fixed_tilt(1).ipynb` :

-  CSV  `AgriPV/results/Linrui_fixed_tilt_scenarios.csv`.


`single_axis(1).ipynb`, `vertical_pv(1).ipynb` .  Linrui CSV.  ZIP  CSV Open field;  `hao_ground_irradiance_SCHEMA_SAMPLE_not_real_data.csv` , .




```python
from tianze_ground_reader import read_ground_csv

records = read_ground_csv("Linrui_fixed_tilt_scenarios.csv", "fixed_tilt")
ordinary = [row for row in records if row["panel_type"] == "conventional"]
semi = [row for row in records if row["panel_type"] == "semi_transparent"]
```




>  Linrui  ground_summary .  Linrui_fixed_tilt_scenarios.csv, Linrui_single_axis_scenarios.csv, Linrui_vertical_pv_scenarios.csv , , , , .  WOFOST ;  CSV , , , , , /Sampling point EPW. , /. , . .
