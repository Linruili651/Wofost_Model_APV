"""Consume complete daily radiation; run pointwise PP/WLP and plot six PV cases."""
from pathlib import Path
from dataclasses import asdict
import hashlib, json, sys, time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
from project_paths import load_crop
ce=load_crop()
ce.load_pcse()
from legacy_bridge import replace_with_retry
MODELS = ('fixed_tilt',)
CASES = [m+'_'+p for m in MODELS for p in ('conventional','semi_transparent')]
CROP_LABELS = dict(winter_wheat='Winter wheat',spring_barley='Spring barley',grain_maize='Grain maize',
                   potato='Potato',sugar_beet='Sugar beet',soybean='Soybean')
LABELS = ['Open field','Fixed\nopaque','Fixed\nsemi-transparent']

def save(path, obj):
    # The shared writer normalises crop-calendar date keys before JSON encoding.
    try:
        ce.save_json(path,obj)
    except PermissionError:
        if Path(path)==HERE/'status.json':
            print('PROGRESS DISPLAY WARNING: status.json is locked; scientific calculation continues.',flush=True)
        else:
            raise  # Required scientific results must never be silently discarded.

def save_csv(frame,path,*,index=False):
    path=Path(path);temporary=path.with_name(path.name+'.tmp')
    frame.to_csv(temporary,index=index)
    replace_with_retry(temporary,path)

def collect():
    assert (HERE/'radiation_complete.json').exists(), 'Full radiation not complete'
    dates = list(pd.date_range('2001-10-15','2002-10-31').date)
    ground=[]; weather=[]
    for model in MODELS:
        for day in dates:
            folder=HERE/'radiation'/model/str(day)
            record=json.loads((folder/'complete.json').read_text(encoding='utf-8'))
            assert record['status']=='passed' and record['hours']==24 and not record['pilot']
            g=pd.read_csv(folder/'ground_daily.csv'); assert len(g)==450
            ground.append(g)
            h=pd.read_csv(folder/'hourly_weather.csv')
            assert len(h)==24
            if model==MODELS[0]:
                t=h.DryBulb.to_numpy(); dew=h.temp_dew.to_numpy()
                weather.append(dict(day=day,TMIN=float(t.min()),TMAX=float(t.max()),TEMP=float(t.mean()),
                    VAP=float(np.mean(6.108*np.exp(17.27*dew/(dew+237.3)))),
                    WIND=float(h.Wspd.mean()),IRRAD=float(h.GHI.sum())*3600,
                    DHI_Wh_m2_day=float(h.DHI.sum())))
            else:
                reference=pd.read_csv(HERE/'radiation'/MODELS[0]/str(day)/'hourly_weather.csv')
                assert np.allclose(h[['GHI','DNI','DHI','DryBulb','Wspd']],reference[['GHI','DNI','DHI','DryBulb','Wspd']])
    g=pd.concat(ground,ignore_index=True);g['day']=pd.to_datetime(g.day).dt.date
    assert not g.duplicated(['scenario_id','point_id','day']).any()
    assert np.isfinite(g.total_Wh_m2_day).all() and g.total_Wh_m2_day.ge(0).all()
    w=pd.DataFrame(weather).set_index('day')
    save_csv(w,HERE/'matched_daily_weather.csv',index=True)
    return g,w

def draw(table):
    dest=HERE/'figures';dest.mkdir(exist_ok=True)
    colors=['#708090','#226e9d','#7bb5d2','#207952','#92c69a','#be742e','#e5b772']
    for crop,spec in ce.crop_catalog().items():
        for mode in ('PP','WLP_MLWB'):
            data=table[(table.crop_id==crop)&(table['mode']==mode)].set_index('scenario_id').loc[['open_field']+CASES]
            fig,axes=plt.subplots(1,2,figsize=(14,5.8))
            fig.subplots_adjust(left=.065,right=.985,bottom=.30,top=.78,wspace=.25)
            fig.suptitle(f"{CROP_LABELS[crop]} | {'PP' if mode=='PP' else 'WLP (layered soil)'}",fontsize=17,x=.065,ha='left')
            fig.text(.065,.85,'Aachen synthetic TMY | Uncalibrated scenario simulations | Equal 1,024 m² plots',fontsize=10)
            axes[0].bar(range(len(LABELS)),data.yield_t_DM_ha,color=colors[:len(LABELS)])
            axes[1].bar(range(len(LABELS)),data.transpiration_mm,color='#447aab',label='Transpiration')
            axes[1].bar(range(len(LABELS)),data.soil_evaporation_mm,bottom=data.transpiration_mm,color='#91b7a1',label='Soil evaporation')
            for ax,title,unit in zip(axes,['Harvest-organ dry-matter yield','Seasonal evapotranspiration'],['t DM ha$^{-1}$','mm']):
                ax.set_title(title,loc='left',fontsize=12);ax.set_ylabel(unit)
                ax.set_xticks(range(len(LABELS)),LABELS,fontsize=8);ax.set_axisbelow(True);ax.grid(axis='y',alpha=.2)
                ax.spines[['top','right']].set_visible(False)
            for i,(_,row) in enumerate(data.iterrows()):
                if pd.isna(row.yield_t_DM_ha):axes[0].text(i,.08,'Not all points\nmature',ha='center',fontsize=7,transform=axes[0].get_xaxis_transform())
            axes[1].legend(frameon=False,fontsize=8)
            fig.text(.065,.14,'Pointwise crop simulations; area-weighted outputs. ET is not irrigation demand.',fontsize=9)
            fig.text(.065,.095,'Original example geometries and optics; low ray-tracing accuracy, 15 × 15 grid; numerical convergence not established.',fontsize=8)
            fig.text(.065,.055,'Fixed tilt only: tracking and vertical systems not evaluated. Uniform rain; no APV microclimate feedbacks.',fontsize=8)
            for ext in ('png','pdf','svg'):fig.savefig(dest/f'{crop}_{mode}.{ext}',dpi=220)
            plt.close(fig)

def main():
    radiation,weather=collect();grid=ce.GroundGrid(**json.loads((HERE/'grid.json').read_text()))
    points=grid.points(); rows=[]
    for crop in ce.crop_catalog():
        for mode in ('PP','WLP_MLWB'):
            config=ce.ModelConfig(crop_id=crop,mode=mode,accept_demo_assumptions=True)
            frame,info=ce.prepare_weather(config)
            matched=weather.loc[list(frame.day)]
            for col in matched:frame[col]=matched[col].to_numpy()
            for case in ['open_field']+CASES:
                folder=HERE/'crop_results'/crop/mode/case;folder.mkdir(parents=True,exist_ok=True)
                summary_path=folder/'summary.json'
                if summary_path.exists():
                    rows.append(json.loads(summary_path.read_text(encoding='utf-8')));continue
                save_csv(frame,folder/'model_weather.csv')
                checkpoint=folder/'point_summary.csv'
                completed=pd.read_csv(checkpoint).to_dict('records') if checkpoint.exists() else []
                ids={v['point_id'] for v in completed}
                if case=='open_field':jobs=[('whole_plot',1024.,frame.IRRAD.to_numpy())]
                else:
                    selected=radiation[(radiation.scenario_id==case)&radiation.day.isin(frame.day)]
                    # Total irradiance is the WOFOST input; direct/diffuse residual is diagnostic only.
                    selected=ce.validate_radiation(frame,selected.drop(columns=['direct_Wh_m2_day','diffuse_residual_Wh_m2_day']),case,grid)
                    jobs=[(p.point_id,p.cell_area_m2,selected[selected.point_id==p.point_id].set_index('day').loc[list(frame.day),'total_Wh_m2_day'].to_numpy()*3600) for p in points.itertuples()]
                # Repair first-point metadata if an older run checkpointed the
                # point before its parameter export failed.
                if completed and (not (folder/'parameters.json').exists() or not (folder/'first_point_daily.csv').exists()):
                    first=ce.run_point(frame,config,radiation=jobs[0][2])
                    save(folder/'parameters.json',dict(config=asdict(config),parameters=first['crop_parameters'],soil=first['soil'],site=first['site'],management=first['management'],weather_provenance=info))
                    save_csv(first['daily'],folder/'first_point_daily.csv')
                for pid,area,rad in jobs:
                    if pid in ids:continue
                    result=ce.run_point(frame,config,radiation=rad)
                    completed.append(dict(point_id=pid,cell_area_m2=area,usable=result['usable'],mature=result['mature'],
                        storage_organ_DM_kg_ha=result['storage_organ_DM_kg_ha'],
                        end_date=str(result['daily'].day.iloc[-1]),water_balance_residual_mm=result['water_balance_residual_mm'],**result['water']))
                    save_csv(pd.DataFrame(completed),checkpoint)
                    save(HERE/'status.json',dict(phase='crops',status='running',crop=crop,mode=mode,case=case,completed_points=len(completed),total_points=len(jobs)))
                    if len(completed)==1:
                        save(folder/'parameters.json',dict(config=asdict(config),parameters=result['crop_parameters'],soil=result['soil'],site=result['site'],management=result['management'],weather_provenance=info))
                        save_csv(result['daily'],folder/'first_point_daily.csv')
                p=pd.DataFrame(completed)
                avg=lambda col:float(np.average(p[col],weights=p.cell_area_m2))
                row=dict(crop_id=crop,mode=mode,scenario_id=case,field_validated=False,
                    yield_t_DM_ha=avg('storage_organ_DM_kg_ha')/1000 if p.usable.all() else None,
                    all_points_usable=bool(p.usable.all()),all_points_mature=bool(p.mature.all()),
                    transpiration_mm=avg('transpiration_mm'),soil_evaporation_mm=avg('soil_evaporation_mm'),
                    et_mm=avg('transpiration_mm')+avg('soil_evaporation_mm'),irrigation_requirement_mm=None,
                    max_water_balance_residual_mm=None if mode=='PP' else float(p.water_balance_residual_mm.abs().max()))
                save(summary_path,row);rows.append(row)
                save_csv(pd.DataFrame(rows),HERE/'comparison_metrics_partial.csv')
                print('CROP COMPLETE',crop,mode,case,flush=True)
    table=pd.DataFrame(rows);assert len(table)==36
    save_csv(table,HERE/'comparison_metrics.csv')
    draw(table)
    from export_results import main as export_results
    export_results()
    save(HERE/'status.json',dict(phase='complete',status='complete',comparisons=36,figures=13,
        crop_specific_figures=12,summary_figures=1,field_validated=False))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
