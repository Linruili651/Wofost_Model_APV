"""Publish 36 paired cases and six crop tables; normalised figures only."""
from pathlib import Path
import json,shutil,hashlib,sys,math
import pandas as pd
import numpy as np
A=Path(__file__).resolve().parent;ROOT=A.parents[1];PIPE=ROOT/'07_Full_Season_Run'
CROPS={'winter_wheat':('Winter wheat','Winter wheat'),'spring_barley':('Spring barley','Spring barley'),
       'grain_maize':('Grain maize','Grain maize'),'potato':('Potato','Potato'),
       'sugar_beet':('Sugar beet','Sugar beet'),'soybean':('Soybean','Soybean')}
CASES={'open_field':'Open field','fixed_tilt_conventional':'Conventional fixed-tilt PV','fixed_tilt_semi_transparent':'Semi-transparent fixed-tilt PV'}
KEYS=['crop_id','mode','scenario_id']
METRICS=['yield_t_DM_ha','transpiration_mm','soil_evaporation_mm','et_mm']
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def markdown(frame):
    def fmt(v):
        if pd.isna(v):return 'Not applicable'
        if isinstance(v,(float,np.floating)):return f'{v:.12g}'
        return str(v)
    return '\n'.join(['| '+' | '.join(map(str,frame.columns))+' |','|'+'|'.join(['---']*len(frame.columns))+'|']+
        ['| '+' | '.join(fmt(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)])
def build():
    out=A/'01_36_Case_Comparison_and_Crop_Tables';out.mkdir(exist_ok=True)
    old=pd.read_csv(A/'previous_run_baseline/comparison_metrics.csv',float_precision='round_trip')
    new=pd.read_csv(A/'pp/comparison_metrics.csv',float_precision='round_trip')
    for t in (old,new):
        assert len(t)==36 and not t.duplicated(KEYS).any()
        assert set(map(tuple,t[KEYS].to_numpy()))=={(c,m,s) for c in CROPS for m in ('PP','WLP_MLWB') for s in CASES}
    old=old.set_index(KEYS);new=new.set_index(KEYS).reindex(old.index)
    data=[];summary=[]
    for key,row in new.iterrows():
        before=old.loc[key];r=dict(zip(KEYS,key));r.update(crop_name_cn=CROPS[key[0]][0],model_version='7.3')
        same=True;exact=True;report_same=True
        for metric in METRICS:
            n=float(row[metric]);o=float(before[metric]);d=n-o
            tol=1e-10 if metric=='yield_t_DM_ha' else 1e-8
            agree=(math.isnan(n) and math.isnan(o)) or (math.isfinite(n) and math.isfinite(o) and abs(d)<=tol)
            r.update({metric+'_previous':o,metric+'_rerun':n,metric+'_difference':d})
            same&=agree;exact&=(n==o or math.isnan(n) and math.isnan(o))
            report_same&=(round(n,2)==round(o,2) or math.isnan(n) and math.isnan(o))
        flag_same=all(row[f]==before[f] for f in ('all_points_mature','all_points_usable','field_validated'))
        r.update(numerically_equivalent=bool(same and flag_same),exact_float_equal=bool(exact and flag_same),
            same_at_2_decimal_places=bool(report_same and flag_same),maturity_and_usability_unchanged=bool(flag_same))
        data.append(r)
    comparison=pd.DataFrame(data)
    comparison.to_csv(out/'36_Cases_Previous_vs_Rerun.csv',index=False,encoding='utf-8-sig')
    raw=new.reset_index();raw.to_csv(out/'36_Cases_Rerun_Results.csv',index=False,encoding='utf-8-sig')
    norm=pd.read_csv(A/'pp/normalised_yield_ET.csv',float_precision='round_trip').set_index(KEYS)
    norm.to_csv(out/'36_Cases_Normalised_Results.csv',encoding='utf-8-sig')
    workbook_data=dict(summary=[],crops=[],comparison=comparison.where(pd.notna(comparison),None).to_dict('records'))
    md=['# 36','',
        ': WOFOST 7.3. 36 × PP/WLP × Light treatment. , CSV. ',
        't/ha; mm/. ET=+, . ','']
    for crop,(cn,en) in CROPS.items():
        g=raw[raw.crop_id==crop].copy()
        g['_m']=g['mode'].map({'PP':0,'WLP_MLWB':1});g['_s']=g.scenario_id.map({s:i for i,s in enumerate(CASES)})
        g=g.sort_values(['_m','_s']);rows=[];paired=[]
        for _,r in g.iterrows():
            k=(crop,r['mode'],r.scenario_id);nr=norm.loc[k];dr=comparison[(comparison.crop_id==crop)&(comparison['mode']==r['mode'])&(comparison.scenario_id==r.scenario_id)].iloc[0]
            rows.append({'Mode':r['mode'],'Light treatment':CASES[r.scenario_id],'Yield_tDM_ha':r.yield_t_DM_ha,
                'Transpiration_mm':r.transpiration_mm,'Soil_evaporation_mm':r.soil_evaporation_mm,'ET_mm':r.et_mm,
                'Relative yield':nr.relative_yield,'Relative_ET':nr.relative_et,
                'Harvest reportable at all points':bool(r.all_points_usable),'All points mature':bool(r.all_points_mature)})
            paired.append({'Mode':r['mode'],'Light treatment':CASES[r.scenario_id],
                'Previous_yield_tDM_ha':dr.yield_t_DM_ha_previous,'Current_yield_tDM_ha':dr.yield_t_DM_ha_rerun,'Yield_difference_tDM_ha':dr.yield_t_DM_ha_difference,
                'Previous_ET_mm':dr.et_mm_previous,'Current_ET_mm':dr.et_mm_rerun,'ET_difference_mm':dr.et_mm_difference,
                'Numerically identical':bool(dr.numerically_equivalent)})
        table=pd.DataFrame(rows);pair=pd.DataFrame(paired)
        table.to_csv(out/(crop+'_Results.csv'),index=False,encoding='utf-8-sig')
        pair.to_csv(out/(crop+'_Previous_vs_Rerun.csv'),index=False,encoding='utf-8-sig')
        text=f'# {cn} / {en}\n\nWOFOST 7.3; PPWLPModeOpen field. \n\n'+markdown(table)+'\n\n## Comparison with previous run\n\n'+markdown(pair)+'\n'
        (out/(crop+'_Data_Table.md')).write_text(text,encoding='utf-8-sig')
        md+=['## '+cn,'',markdown(table),'','Comparison with previous run: ','',markdown(pair),'']
        workbook_data['crops'].append(dict(crop_id=crop,name=cn,results=rows,comparison=paired))
    (out/'Six_Crop_Tables_and_Case_Comparisons.md').write_text('\n'.join(md),encoding='utf-8-sig')
    metrics={m:float(comparison[m+'_difference'].abs().max()) for m in METRICS}
    report=dict(total_cases=36,numerically_equivalent_cases=int(comparison.numerically_equivalent.sum()),
        exact_float_equal_cases=int(comparison.exact_float_equal.sum()),same_at_2_decimal_places_cases=int(comparison.same_at_2_decimal_places.sum()),
        status_flags_identical=bool(comparison.maturity_and_usability_unchanged.all()),max_abs_summary_differences=metrics,
        tolerances=dict(yield_t_DM_ha=1e-10,water_mm=1e-8),pointwise_check='pp_comparison.json',
        all_source_manifest_files_unchanged=all(r['same'] for r in json.loads((A/'old_manifest_comparison.json').read_text(encoding='utf-8'))),
        discarded_first_pass_reason='CSV serialization/reload perturbed double precision weather; final rerun uses lossless pickle of the original in-memory weather',
        evidence='difference_investigation.json; three worst discrepant point rechecks exactly reproduce previous values',
        model_version='7.3',radiance_executed=False)
    save(out/'36_Case_Comparison_Conclusion.json',report)
    workbook_data['summary']=report;save(out/'workbook_data.json',workbook_data)
    figures=A/'02_Normalised_Figures';figures.mkdir(exist_ok=True)
    for p in (A/'pp/figures').glob('Summary_Relative_Yield_vs_Relative_ET.*'):
        shutil.copy2(p,figures/('WOFOST73_36Cases_Normalised_Yield_ET'+p.suffix))
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    return report
def managed_tables():
    source=A/'08_Thesis_Results/05_Target_Inputs/01_Tables/Managed_Water_Nitrogen_Comparison.csv'
    if not source.exists():return
    out=A/'03_Managed_Water_Nitrogen_Tables';out.mkdir(exist_ok=True)
    t=pd.read_csv(source,float_precision='round_trip');assert len(t)==18
    columns={'scenario_id':'Light treatment','yield_t_DM_ha':'Yield_tDM_ha','common_yield_target_t_DM_ha':'_tDM_ha',
        'target_achieved':'Target achieved','transpiration_mm':'Transpiration_mm','soil_evaporation_mm':'Soil_evaporation_mm','et_mm':'ET_mm',
        'net_irrigation_mm':'Net_irrigation_mm','fertiliser_N_kg_ha':'Fertiliser_N_kgN_ha','nitrogen_leaching_kg_N_ha':'Nitrogen_leaching_kgN_ha'}
    all_md=['# WOFOST 8.1Data_Table','',
        '187.3. Open fieldPP8190%; . ','']
    for crop,(cn,en) in CROPS.items():
        g=t[t.crop_id==crop][list(columns)].rename(columns=columns).copy();g['Light treatment']=g['Light treatment'].map(CASES)
        g.to_csv(out/(crop+'_Managed_Results.csv'),index=False,encoding='utf-8-sig')
        text='# '+cn+': WOFOST 8.1\n\n'+markdown(g)+'\n'
        (out/(crop+'_Managed_Scenario_Table.md')).write_text(text,encoding='utf-8-sig');all_md+=['## '+cn,'',markdown(g),'']
    (out/'Six_Crop_Managed_Water_Nitrogen_Tables.md').write_text('\n'.join(all_md),encoding='utf-8-sig')
    old=pd.read_csv(ROOT/'08_Thesis_Results/05_Target_Inputs/01_Tables/Managed_Water_Nitrogen_Comparison.csv',float_precision='round_trip').set_index(['crop_id','scenario_id'])
    cur=t.set_index(['crop_id','scenario_id']).reindex(old.index)
    metrics=['yield_t_DM_ha','net_irrigation_mm','fertiliser_N_kg_ha','nitrogen_leaching_kg_N_ha','et_mm']
    diffs=[]
    for key,row in cur.iterrows():
        v=dict(crop_id=key[0],scenario_id=key[1])
        for metric in metrics:v[metric+'_difference']=float(row[metric]-old.loc[key,metric])
        v['target_status_unchanged']=bool(row.target_status==old.loc[key,'target_status']);diffs.append(v)
    pd.DataFrame(diffs).to_csv(out/'18_Managed_Cases_Previous_vs_Rerun.csv',index=False,encoding='utf-8-sig')
    save(out/'Managed_Comparison_Conclusion.json',dict(cases=18,max_abs_differences={m:max(abs(r[m+'_difference']) for r in diffs) for m in metrics},
        target_achieved_cases=int(t.target_achieved.sum()),all_irrigation_zero=bool((t.net_irrigation_mm==0).all()),
        target_statuses_unchanged=all(r['target_status_unchanged'] for r in diffs)))
if __name__=='__main__':build();managed_tables()
