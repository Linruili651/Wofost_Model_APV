from pathlib import Path
import sys,json,importlib.util,os,hashlib
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
A=Path(__file__).resolve().parent;ROOT=A.parents[1];P=ROOT/'07_Full_Season_Run';sys.path.insert(0,str(P))
import pandas as pd
import numpy as np
import run_crops_and_plots as c
rad,w=c.collect();w.to_pickle(A/'original_in_memory_weather.pkl')
roundtrip=pd.read_csv(A/'pp/matched_daily_weather.csv');roundtrip.day=pd.to_datetime(roundtrip.day).dt.date;roundtrip=roundtrip.set_index('day')
weather_diff={col:float(np.abs(w[col].to_numpy()-roundtrip[col].to_numpy()).max()) for col in w}
pd.DataFrame([dict(day=str(day),variable=col,original=float(w.at[day,col]),csv_reloaded=float(roundtrip.at[day,col]),difference=float(roundtrip.at[day,col]-w.at[day,col]))
    for day in w.index for col in w if w.at[day,col]!=roundtrip.at[day,col]]).to_csv(A/'weather_roundtrip_differences.csv',index=False)
cases=json.loads((A/'pp_comparison.json').read_text())
records=[]
for case in cases:
    if case['passed']:continue
    crop,mode,scenario=Path(case['case']).parts
    old=pd.read_csv(P/'crop_results'/crop/mode/scenario/'point_summary.csv').set_index('point_id')
    fresh=pd.read_csv(A/'pp/crop_results'/crop/mode/scenario/'point_summary.csv').set_index('point_id')
    delta=np.abs(old.storage_organ_DM_kg_ha-fresh.storage_organ_DM_kg_ha)
    pid=delta.idxmax()
    cfg=c.ce.ModelConfig(crop_id=crop,mode=mode,accept_demo_assumptions=True)
    frame,_=c.ce.prepare_weather(cfg)
    for col in w:frame[col]=w.loc[list(frame.day),col].to_numpy()
    selected=rad[(rad.scenario_id==scenario)&rad.day.isin(frame.day)]
    selected=c.ce.validate_radiation(frame,selected.drop(columns=['direct_Wh_m2_day','diffuse_residual_Wh_m2_day']),scenario,c.ce.GroundGrid(**json.loads((P/'grid.json').read_text())))
    light=selected[selected.point_id==pid].set_index('day').loc[list(frame.day),'total_Wh_m2_day'].to_numpy()*3600
    with np.load(A/'target_resource_run'/(scenario+'_radiation.npz')) as z:
        ix=pd.Index(z['days']).get_indexer([str(d) for d in frame.day]);j=list(z['point_ids']).index(pid);light_npz=z['light_J_m2_day'][ix,j]
    result=c.ce.run_point(frame,cfg,radiation=light)
    r=dict(crop_id=crop,mode=mode,scenario_id=scenario,point_id=pid,old_yield_kg_ha=float(old.at[pid,'storage_organ_DM_kg_ha']),
        csv_roundtrip_rerun_yield_kg_ha=float(fresh.at[pid,'storage_organ_DM_kg_ha']),original_input_recheck_yield_kg_ha=result['storage_organ_DM_kg_ha'],
        difference_vs_old_kg_ha=float(result['storage_organ_DM_kg_ha']-old.at[pid,'storage_organ_DM_kg_ha']),
        npz_radiation_max_difference=float(np.abs(light-light_npz).max()))
    records.append(r);print(json.dumps(r),flush=True)
files=json.loads((P/'execution_manifest.json').read_text(encoding='utf-8'));hashes=[]
for rel,oldhash in files.items():
    path=ROOT/rel;newhash=hashlib.sha256(path.read_bytes()).hexdigest()
    hashes.append(dict(path=rel,old_sha256=oldhash,current_sha256=newhash,same=oldhash==newhash))
c.ce.save_json(A/'old_manifest_comparison.json',hashes)
c.ce.save_json(A/'difference_investigation.json',dict(weather_CSV_roundtrip_max_abs_changes=weather_diff,point_rechecks=records))
print('DIFFERENCE_INVESTIGATION_COMPLETE',flush=True)
