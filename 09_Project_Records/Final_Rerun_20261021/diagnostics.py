from pathlib import Path
import runpy,json,os,sys
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[1]
registry=runpy.run_path(str(ROOT/'06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
base=registry['install']()
import pandas as pd
import numpy as np
w=pd.read_csv(AUDIT/'pp/matched_daily_weather.csv');w.day=pd.to_datetime(w.day).dt.date;w=w.set_index('day')
rows=[]
for crop in base.crop_catalog():
    cfg=base.ModelConfig(crop_id=crop,accept_demo_assumptions=True)
    raw,_=base.prepare_weather(cfg);matched=w.loc[list(raw.day)]
    a=raw.IRRAD.sum()/1e6;b=matched.IRRAD.sum()/1e6
    rows.append(dict(crop_id=crop,raw_EPW_shortwave_MJ_m2=float(a),radiation_matched_open_field_MJ_m2=float(b),
        difference_percent=float((b/a-1)*100),max_daily_difference_MJ_m2=float(np.max(np.abs(raw.IRRAD.to_numpy()-matched.IRRAD.to_numpy()))/1e6),
        max_TMIN_difference_C=float(np.max(np.abs(raw.TMIN.to_numpy()-matched.TMIN.to_numpy()))),
        max_WIND_difference_m_s=float(np.max(np.abs(raw.WIND.to_numpy()-matched.WIND.to_numpy())))))
pd.DataFrame(rows).to_csv(AUDIT/'open_field_weather_source_comparison.csv',index=False)
base.save_json(AUDIT/'open_field_weather_source_comparison.json',rows)
ext=ROOT/'02_WLP_Model/Nitrogen_Extension'
e=runpy.run_path(str(ext/'Resource_Target_Engine.py'));n=e['n']
cfg=n.NitrogenConfig(crop_id='winter_wheat',nitrogen_inputs='04_Soil_and_Python/Nitrogen_Inputs/Aachen_BK50_SoilGrids_Target.json',accept_reference_scenario=True,accept_demo_assumptions=True)
data=n.load_inputs(cfg);frame,_=base.prepare_weather(cfg.base_config())
matched=w.loc[list(frame.day)]
for col in matched:frame[col]=matched[col].to_numpy()
frame['RAIN_mm_day']=0.
policy=json.loads((ext/'Target_Management.json').read_text(encoding='utf-8'))
result=e['run_point'](frame,cfg,data,frame.IRRAD.to_numpy(),policy)
folder=AUDIT/'diagnostic_only_forced_dry';folder.mkdir(exist_ok=True)
frame.to_csv(folder/'synthetic_weather_NOT_formal_results.csv',index=False)
for k in ('daily','soil_daily','actions'):result[k].to_csv(folder/(k+'.csv.gz'),index=False,compression='gzip')
base.save_json(folder/'metrics.json',dict(purpose='Synthetic zero-rainfall diagnostic only; excluded from all formal treatment tables',**result['metrics']))
assert result['metrics']['net_irrigation_mm']>0
assert abs(result['metrics']['water_balance_residual_mm'])<.001
assert abs(result['metrics']['nitrogen_balance_residual_kg_N_ha'])<.001
assert result['actions'].net_irrigation_mm.max()<=5+1e-10
base.save_json(AUDIT/'controller_diagnostic.json',dict(status='passed',synthetic=True,excluded_from_formal_results=True,
    irrigation_trigger_test_mm=result['metrics']['net_irrigation_mm'],max_daily_irrigation_mm=float(result['actions'].net_irrigation_mm.max()),
    water_balance_residual_mm=result['metrics']['water_balance_residual_mm'],nitrogen_balance_residual_kg_N_ha=result['metrics']['nitrogen_balance_residual_kg_N_ha']))
print(json.dumps(rows,indent=2),flush=True)
print('CONTROLLER_DIAGNOSTIC_PASSED',flush=True)
