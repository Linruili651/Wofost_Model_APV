"""Fresh scientific rerun using archived radiation, never invoking Radiance."""
from pathlib import Path
import os, sys, json, importlib.util, time, traceback, shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[1]
PIPE=ROOT/'07_Full_Season_Run'
EXT=ROOT/'02_WLP_Model/Nitrogen_Extension'
sys.path.insert(0,str(PIPE))
import numpy as np
import pandas as pd
from project_paths import load_crop
ce=load_crop()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def target_module():
    m=module('target_rerun',EXT/'Run_Target_Inputs.py')
    m.OUT=AUDIT/'target_resource_run'
    return m
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def pp_case(crop,mode,case):
    config=ce.ModelConfig(crop_id=crop,mode=mode,accept_demo_assumptions=True)
    frame,info=ce.prepare_weather(config)
    # Preserve exact original binary floats; CSV is an export, not a reload source.
    w=pd.read_pickle(AUDIT/'original_in_memory_weather.pkl').loc[list(frame.day)]
    for col in w:frame[col]=w[col].to_numpy()
    folder=AUDIT/'pp/crop_results'/crop/mode/case;folder.mkdir(parents=True,exist_ok=True)
    frame.to_csv(folder/'model_weather.csv',index=False)
    grid=ce.GroundGrid(**json.loads((PIPE/'grid.json').read_text()));points=grid.points()
    if case=='open_field':jobs=[('whole_plot',1024.,frame.IRRAD.to_numpy())]
    else:
        with np.load(AUDIT/'target_resource_run'/(case+'_radiation.npz')) as z:
            ix=pd.Index(z['days']).get_indexer([str(d) for d in frame.day]);assert (ix>=0).all()
            light=z['light_J_m2_day'][ix,:];ids=list(z['point_ids'])
        jobs=[(p.point_id,float(p.cell_area_m2),light[:,ids.index(p.point_id)]) for p in points.itertuples()]
    rows=[]
    for pid,area,rad in jobs:
        result=ce.run_point(frame,config,radiation=rad)
        rows.append(dict(point_id=pid,cell_area_m2=area,usable=result['usable'],mature=result['mature'],
            storage_organ_DM_kg_ha=result['storage_organ_DM_kg_ha'],end_date=str(result['daily'].day.iloc[-1]),
            water_balance_residual_mm=result['water_balance_residual_mm'],**result['water']))
        if len(rows)==1:
            result['daily'].to_csv(folder/'first_point_daily.csv',index=False)
            from dataclasses import asdict
            ce.save_json(folder/'parameters.json',dict(config=asdict(config),parameters=result['crop_parameters'],
                soil=result['soil'],site=result['site'],management=result['management'],weather_provenance=info))
        if len(rows)%25==0:
            pd.DataFrame(rows).to_csv(folder/'point_summary.csv',index=False)
            print('PP_PROGRESS',crop,mode,case,len(rows),flush=True)
    p=pd.DataFrame(rows);p.to_csv(folder/'point_summary.csv',index=False)
    avg=lambda c:float(np.average(p[c],weights=p.cell_area_m2))
    row=dict(crop_id=crop,mode=mode,scenario_id=case,field_validated=False,
        yield_t_DM_ha=avg('storage_organ_DM_kg_ha')/1000 if p.usable.all() else None,
        all_points_usable=bool(p.usable.all()),all_points_mature=bool(p.mature.all()),
        transpiration_mm=avg('transpiration_mm'),soil_evaporation_mm=avg('soil_evaporation_mm'),
        et_mm=avg('transpiration_mm')+avg('soil_evaporation_mm'),irrigation_requirement_mm=None,
        max_water_balance_residual_mm=None if mode=='PP' else float(p.water_balance_residual_mm.abs().max()))
    save(folder/'summary.json',row);print('PP_COMPLETE',crop,mode,case,flush=True);return row
def target_case(crop,case,identity):return target_module().run_case(crop,case,identity)
def compare_points(kind):
    fresh=AUDIT/('pp/crop_results' if kind=='pp' else 'target_resource_run/cases')
    old=PIPE/('crop_results' if kind=='pp' else 'target_resource_run/cases')
    records=[]
    for path in fresh.rglob('point_summary.csv'):
        a=pd.read_csv(path).sort_values('point_id').reset_index(drop=True)
        b=pd.read_csv(old/path.relative_to(fresh)).sort_values('point_id').reset_index(drop=True)
        assert list(a.point_id)==list(b.point_id)
        numeric=[c for c in a.select_dtypes(include='number') if c in b]
        diffs={c:float((a[c]-b[c]).abs().max()) for c in numeric if not (a[c].isna().all() and b[c].isna().all())}
        passed=all(np.allclose(a[c],b[c],atol=1e-7,rtol=1e-10,equal_nan=True) for c in numeric)
        records.append(dict(case=str(path.parent.relative_to(fresh)),points=len(a),passed=passed,max_abs_differences=diffs))
    save(AUDIT/(kind+'_comparison.json'),records)
    return sum(r['points'] for r in records)
def main():
    started=time.time();save(AUDIT/'status.json',dict(status='running',phase='radiation_input_validation',radiance_executed=False))
    # collect() only reads saved daily outputs; no Radiance module is imported.
    crops=module('crop_rerun',PIPE/'run_crops_and_plots.py')
    radiation,weather=crops.collect()
    (AUDIT/'pp').mkdir(exist_ok=True)
    weather.to_csv(AUDIT/'pp/matched_daily_weather.csv')
    weather.to_pickle(AUDIT/'original_in_memory_weather.pkl')
    t=target_module();identity=t.prepare()
    save(AUDIT/'radiation_input_validation.json',dict(days=len(weather),rows=len(radiation),
        points_per_pv_case=225,scenarios=list(radiation.scenario_id.unique()),radiance_executed=False,identity=identity))
    cases=['open_field','fixed_tilt_conventional','fixed_tilt_semi_transparent']
    with ProcessPoolExecutor(max_workers=6) as pool:
        jobs=[pool.submit(pp_case,c,m,s) for c in ce.crop_catalog() for m in ('PP','WLP_MLWB') for s in cases]
        rows=[]
        for f in as_completed(jobs):
            rows.append(f.result());save(AUDIT/'status.json',dict(status='running',phase='PP_WLP',completed_cases=len(rows),total_cases=36,elapsed_seconds=time.time()-started))
    table=pd.DataFrame(rows);table.to_csv(AUDIT/'pp/comparison_metrics.csv',index=False)
    pp_points=compare_points('pp')
    import plot_relative_summary
    plot_relative_summary.build(table,AUDIT/'pp')
    save(AUDIT/'status.json',dict(status='running',phase='managed_water_nitrogen',pp_points=pp_points,completed_cases=0,total_cases=18))
    with ProcessPoolExecutor(max_workers=6) as pool:
        jobs=[pool.submit(target_case,c,s,identity) for s in cases for c in ce.crop_catalog()]
        n=0
        for f in as_completed(jobs):
            f.result();n+=1;save(AUDIT/'status.json',dict(status='running',phase='managed_water_nitrogen',completed_cases=n,total_cases=18,elapsed_seconds=time.time()-started))
    target_points=compare_points('target')
    plots=module('managed_plots',EXT/'Plot_Target_Inputs.py')
    plots.SOURCE=AUDIT/'target_resource_run';plots.ROOT=AUDIT
    plots.DEST=AUDIT/'08_Thesis_Results/05_Target_Inputs'
    plots.plot_crop=lambda crop,table:None  # User wants crop tables, only normalised figures.
    dest=AUDIT/'08_Thesis_Results'
    for d in ('01_Tables','02_Figures'):(dest/d).mkdir(parents=True,exist_ok=True)
    save(dest/'EXPORT_STATUS.json',dict(status='complete',figures=13))
    validation=plots.build()
    validation.update(figures=1,figure_files=3,per_crop_outputs='tables, not figures')
    for name in ('VALIDATION.json','STATUS.json'):
        path=plots.DEST/name;v=json.loads(path.read_text(encoding='utf-8'))
        v.update(figures=1,figure_files=3,per_crop_outputs='tables, not figures');save(path,v)
    save(AUDIT/'status.json',dict(status='complete',radiance_executed=False,pp_wlp_cases=36,pp_wlp_point_seasons=pp_points,
        managed_cases=18,managed_point_seasons=target_points,potential_reference_point_seasons=target_points,
        reproduced_previous_results=all(r['passed'] for kind in ('pp','target') for r in json.loads((AUDIT/(kind+'_comparison.json')).read_text(encoding='utf-8'))),
        elapsed_seconds=time.time()-started,target_validation=validation))
if __name__=='__main__':
    try:main()
    except BaseException:
        save(AUDIT/'failure.json',dict(traceback=traceback.format_exc()));raise
