"""Full existing 225-point grid: same adaptive rules and common crop yield target."""
from pathlib import Path
from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
import argparse,gc,hashlib,json,os,runpy,sys,time,traceback
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
E=runpy.run_path(str(HERE/'Resource_Target_Engine-目标投入引擎.py'));N=E['n'];ROOT=E['ROOT']
PIPE=ROOT/'07_Full_Season_Run-完整季运行'
OUT=PIPE/'target_resource_run'
RESULTS=ROOT/'08_Thesis_Results-论文表格与图片'
INPUT='04_Soil_and_Python-土壤条件与Python/Nitrogen_Inputs-氮输入/Aachen_BK50_SoilGrids_Target-目标投入估计情景.json'
CASES=('open_field','fixed_tilt_conventional','fixed_tilt_semi_transparent')
def now():return datetime.now(ZoneInfo('Europe/Berlin')).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):N.base.save_json(p,v)
def csv(frame,path):
    tmp=path.with_name(path.name+'.tmp');frame.to_csv(tmp,index=False)
    __import__('legacy_bridge').replace_with_retry(tmp,path)

def prepare():
    OUT.mkdir(exist_ok=True)
    if not (ROOT/INPUT).exists():runpy.run_path(str(HERE/'Prepare_Target_Inputs-准备目标计算参数.py'))['build']()
    policy=read(HERE/'Target_Management-目标管理.json')
    if not 0<policy['target_fraction_of_open_field_PP81_yield']<=1:raise ValueError('Invalid target')
    if not 0<policy['irrigation_efficiency']<=1:raise ValueError('Invalid irrigation efficiency')
    if policy['fertiliser_fraction_NH4_N']+policy['fertiliser_fraction_NO3_N']!=1:raise ValueError('N fractions must sum to one')
    sources=[ROOT/INPUT,PIPE/'matched_daily_weather.csv',PIPE/'grid.json',Path(__file__),
        HERE/'Resource_Target_Engine-目标投入引擎.py',HERE/'Target_Management-目标管理.json',HERE/'Prepare_Target_Inputs-准备目标计算参数.py']
    sources+=list((ROOT/'06_Hao_Interface_and_Rerun-Hao接口与复跑/Shared_Core-共享核心').glob('*.py'))
    sources+=list((N.INPUTS/'Crop_Parameters_81-WOFOST81作物参数').glob('*.yaml'))
    sources +=[N.INPUTS/'Source_Records-来源记录/SoilGrids_Aachen_C_N_pH.json',
        ROOT/'03_Precipitation-降水条件/Aachen_TMY_Weather-Aachen典型年天气.epw',
        ROOT/'03_Precipitation-降水条件/Precipitation_Supplement-降水补充.json',
        ROOT/'03_Precipitation-降水条件/Precipitation_Adapter-降水适配.py',
        ROOT/'06_Hao_Interface_and_Rerun-Hao接口与复跑/Shared_Inputs-共享输入/Crop_Catalog-作物清单.json']
    parts=[]
    for day in pd.date_range('2001-10-15','2002-10-31').date:
        d=PIPE/'radiation/fixed_tilt'/str(day);record=read(d/'complete.json')
        if record['status']!='passed' or record['hours']!=24 or record['pilot']:raise ValueError('Radiation incomplete')
        g=pd.read_csv(d/'ground_daily.csv')
        if len(g)!=450 or g.duplicated(['scenario_id','point_id']).any():raise ValueError('Invalid radiation grid')
        parts.append(g);sources.extend([d/'ground_daily.csv',d/'complete.json',d/'hourly_weather.csv'])
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    identity=N.base.fingerprint(hashes)
    previous=OUT/'execution_manifest.json'
    if previous.exists() and read(previous)['identity']!=identity:raise ValueError('Inputs changed; do not mix checkpoints')
    save(previous,dict(identity=identity,files=hashes,created_at=now(),scenario='BK50/SoilGrids estimates and reference initial mineral N',
        field_validated=False,all_code_and_inputs_inside_project=True,
        management='Same adaptive rule across light treatments, net water at stated efficiency, ideal mineral-N equivalent',
        target='Per crop: 90% of matched open-field WOFOST81 potential harvest-organ dry-matter yield',
        methods='All original 225 soil columns per PV case. No radiation averaging before model execution.'))
    radiation=pd.concat(parts,ignore_index=True)
    grid=N.base.GroundGrid(**read(PIPE/'grid.json'));points=grid.points()
    for case in CASES[1:]:
        g=radiation[radiation.scenario_id==case]
        pivot=g.pivot(index='day',columns='point_id',values='total_Wh_m2_day').reindex(columns=list(points.point_id))
        if pivot.shape!=(382,225) or not np.isfinite(pivot.to_numpy()).all() or (pivot.to_numpy()<0).any():raise ValueError('Invalid daily radiation')
        path=OUT/(case+'_radiation.npz')
        np.savez_compressed(path,days=pivot.index.to_numpy(str),point_ids=pivot.columns.to_numpy(str),light_J_m2_day=pivot.to_numpy(float)*3600)
    return identity

def run_case(crop,case,identity):
    folder=OUT/'cases'/crop/case;folder.mkdir(parents=True,exist_ok=True)
    if (folder/'summary.json').exists():return read(folder/'summary.json')
    cfg=N.NitrogenConfig(crop_id=crop,nitrogen_inputs=INPUT,accept_reference_scenario=True,accept_demo_assumptions=True)
    pp=N.NitrogenConfig(crop_id=crop,mode='PP81',nitrogen_inputs=INPUT,accept_reference_scenario=True,accept_demo_assumptions=True)
    data=N.load_inputs(cfg);policy=read(HERE/'Target_Management-目标管理.json')
    frame,weather=N.base.prepare_weather(cfg.base_config())
    matched=pd.read_csv(PIPE/'matched_daily_weather.csv');matched.day=pd.to_datetime(matched.day).dt.date
    matched=matched.set_index('day').loc[list(frame.day)]
    for col in matched:frame[col]=matched[col].to_numpy()
    csv(frame,folder/'model_weather.csv')
    grid=N.base.GroundGrid(**read(PIPE/'grid.json'));points=grid.points()
    if case=='open_field':jobs=[('whole_plot',float(points.cell_area_m2.sum()),frame.IRRAD.to_numpy())]
    else:
        with np.load(OUT/(case+'_radiation.npz')) as z:
            ix=pd.Index(z['days']).get_indexer([str(d) for d in frame.day])
            if (ix<0).any():raise ValueError('Missing crop dates')
            light=z['light_J_m2_day'][ix,:];ids=list(z['point_ids'])
        jobs=[(p.point_id,float(p.cell_area_m2),light[:,ids.index(p.point_id)]) for p in points.itertuples()]
    cp=folder/'point_summary.csv';done=pd.read_csv(cp).to_dict('records') if cp.exists() else []
    ids={str(r['point_id']) for r in done}
    for pid,area,radiation in jobs:
        if str(pid) in ids:continue
        potential=N.run_point(frame,pp,data,radiation=radiation)
        if not potential['usable']:raise ValueError('Potential-yield reference unusable')
        ppy=potential['storage_organ_DM_kg_ha'];del potential;gc.collect()
        result=E['run_point'](frame,cfg,data,radiation,policy)
        row=dict(result['metrics'],point_id=pid,cell_area_m2=area,potential_yield_kg_DM_ha=ppy)
        daily=folder/'daily';daily.mkdir(exist_ok=True)
        for key in ('daily','soil_daily','actions'):
            target=daily/f'{pid}_{key}.csv.gz';temp=target.with_name(target.name+'.tmp')
            result[key].to_csv(temp,index=False,compression={'method':'gzip','compresslevel':1,'mtime':0})
            __import__('legacy_bridge').replace_with_retry(temp,target)
        if not (folder/'parameters.json').exists():
            save(folder/'parameters.json',dict(config=asdict(cfg),inputs=data,weather_provenance=weather,
                executed_weather='model_weather.csv: matched daily meteorology plus existing liquid-rain supplement',
                execution_identity=identity,**result['parameters']))
        done.append(row);csv(pd.DataFrame(done),cp)
        save(folder/'progress.json',dict(status='running',crop_id=crop,scenario_id=case,completed_points=len(done),total_points=len(jobs),
            updated_at=now(),pid=os.getpid()))
        if len(done)%10==0:print(crop,case,len(done),len(jobs),flush=True)
        del result;gc.collect()
    t=pd.DataFrame(done)
    if len(t)!=len(jobs) or t.point_id.duplicated().any():raise ValueError('Invalid point checkpoints')
    avg=lambda key:float(np.average(t[key],weights=t.cell_area_m2))
    usable=bool(t.usable.all())
    row=dict(crop_id=crop,scenario_id=case,mode='NWLP81_adaptive_water_N',points=len(t),potential_point_seasons=len(t),
        model_version='8.1',scenario_kind='estimated_reference',field_validated=False,
        all_points_usable=usable,all_points_mature=bool(t.mature.all()),
        yield_t_DM_ha=avg('storage_organ_DM_kg_ha')/1000 if usable else None,
        potential_yield_t_DM_ha=avg('potential_yield_kg_DM_ha')/1000,
        max_water_balance_residual_mm=float(t.water_balance_residual_mm.abs().max()),
        max_nitrogen_balance_residual_kg_N_ha=float(t.nitrogen_balance_residual_kg_N_ha.abs().max()),
        leaching_boundary_depth_cm=sum(l['Thickness'] for l in data['SoilProfileDescription']['SoilLayers']),
        earliest_end_date=min(t.end_date),latest_end_date=max(t.end_date),N_cap_reached_points=int(t.N_cap_reached.sum()),
        execution_identity=identity)
    for key in ['net_irrigation_mm','gross_irrigation_mm','fertiliser_N_kg_ha','nitrogen_leaching_kg_N_ha',
        'nitrate_leaching_kg_N_ha','ammonium_leaching_kg_N_ha','denitrification_kg_N_ha','wet_N_input_kg_N_ha',
        'soil_N_uptake_kg_N_ha','biological_N_fixation_kg_N_ha','top_boundary_N_export_kg_N_ha','drainage_bottom_mm',
        'runoff_mm','transpiration_mm','soil_evaporation_mm','water_stress_days','initial_soil_N_kg_ha','final_soil_N_kg_ha']:
        row[key]=avg(key)
    row['et_mm']=row['transpiration_mm']+row['soil_evaporation_mm']
    save(folder/'summary.json',row)
    save(folder/'progress.json',dict(status='complete',crop_id=crop,scenario_id=case,completed_points=len(jobs),total_points=len(jobs),updated_at=now()))
    print('COMPLETE',crop,case,flush=True);return row

def update(status):
    items=[read(p) for p in (OUT/'cases').glob('*/*/progress.json')]
    status.update(updated_at=now(),completed_managed_point_seasons=sum(p['completed_points'] for p in items),
        completed_cases=sum(p['status']=='complete' for p in items),active=[p for p in items if p['status']=='running'])
    save(OUT/'status.json',status)
    sys.path.insert(0,str(PIPE))
    import watch_progress
    watch_progress.render()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--crop',choices=list(N.base.crop_catalog())+['all'],default='all')
    parser.add_argument('--open-only',action='store_true');args=parser.parse_args()
    identity=prepare();crops=list(N.base.crop_catalog()) if args.crop=='all' else [args.crop]
    cases=['open_field'] if args.open_only else list(CASES)
    status=dict(status='running',phase='target_inputs',pid=os.getpid(),started_at=now(),
        total_cases=len(crops)*len(cases),total_managed_point_seasons=len(crops)*(1 if args.open_only else 451),
        target_fraction=.9,workers=args.workers)
    update(status)
    try:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            pending={pool.submit(run_case,crop,case,identity) for case in cases for crop in crops}
            while pending:
                finished,pending=wait(pending,timeout=10,return_when=FIRST_COMPLETED)
                for f in finished:f.result()
                update(status)
        if args.crop=='all' and not args.open_only:
            plotting=runpy.run_path(str(HERE/'Plot_Target_Inputs-绘制目标投入结果.py'))
            plotting['build']()
            status.update(status='packaging');update(status)
            runpy.run_path(str(ROOT/'09_Project_Records-项目记录/build_hao_delivery.py'))['main']()
        status.update(status='complete',finished_at=now());update(status)
    except BaseException:
        status.update(status='failed',failed_at=now(),traceback=traceback.format_exc());update(status);raise

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
