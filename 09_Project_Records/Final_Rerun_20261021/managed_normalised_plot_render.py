"""Plot actual complete adaptive-input runs, retaining failed yield targets."""
from pathlib import Path
import json,math,shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'06_Hao_Interface_and_Rerun').is_dir())
SOURCE=ROOT/'07_Full_Season_Run/target_resource_run'
DEST=ROOT/'08_Thesis_Results/05_Target_Inputs'
CROPS={'winter_wheat':('Winter wheat','#0072B2'),'spring_barley':('Spring barley','#E69F00'),
    'grain_maize':('Grain maize','#009E73'),'potato':('Potato','#CC79A7'),
    'sugar_beet':('Sugar beet','#D55E00'),'soybean':('Soybean','#7053A3')}
CASES=('open_field','fixed_tilt_conventional','fixed_tilt_semi_transparent')
LABELS=['Open field','Conventional\nPV','Semi-transparent\nPV']

def normalise(table):
    rows=[]
    for crop in CROPS:
        g=table[table.crop_id==crop].set_index('scenario_id')
        baseline=g.loc['open_field']
        for case in CASES:
            row=g.loc[case].to_dict();row.update(crop_id=crop,scenario_id=case)
            for metric in ['yield_t_DM_ha','et_mm','net_irrigation_mm','fertiliser_N_kg_ha','nitrogen_leaching_kg_N_ha']:
                b=baseline[metric];v=row[metric]
                row['open_field_'+metric]=b
                row['relative_'+metric]=v/b if pd.notna(v) and pd.notna(b) and b>0 else None
                row['difference_'+metric]=v-b if pd.notna(v) and pd.notna(b) else None
            rows.append(row)
    return pd.DataFrame(rows)

def savefig(fig,stem):
    folder=DEST/'02_Figures';folder.mkdir(parents=True,exist_ok=True)
    for ext in ('png','pdf','svg'):fig.savefig(folder/f'{stem}.{ext}',dpi=220,facecolor='white')
    plt.close(fig)

def plot_crop(crop,g):
    label,colour=CROPS[crop]
    fig,ax=plt.subplots(1,4,figsize=(17,6.3))
    fig.subplots_adjust(left=.055,right=.985,top=.75,bottom=.32,wspace=.40)
    fig.suptitle(f'{label} | Adaptive irrigation and nitrogen inputs',x=.065,y=.96,ha='left',fontsize=19,weight='bold')
    fig.text(.065,.88,'Estimated soil scenario | WOFOST 8.1 + layered water balance + SNOMIN | Same rules across light treatments',fontsize=10,color='#a84415')
    g=g.set_index('scenario_id').loc[list(CASES)]
    bars=ax[0].bar(range(3),g.yield_t_DM_ha,color=colour,alpha=.8)
    target=g.common_yield_target_t_DM_ha.iloc[0]
    ax[0].axhline(target,ls='--',color='#b33a24',lw=1.2,label='Common yield target')
    for i,(_,r) in enumerate(g.iterrows()):
        if not r.target_achieved:bars[i].set_hatch('//')
        y=r.yield_t_DM_ha
        if pd.notna(y):ax[0].text(i,y,f'{y:.2f}',ha='center',va='bottom',fontsize=8)
        else:ax[0].text(i,.05,'No usable\nharvest',ha='center',fontsize=8,transform=ax[0].get_xaxis_transform())
    ax[0].set(title='Harvest-organ DM yield',ylabel='t DM ha$^{-1}$');ax[0].legend(frameon=False,fontsize=8)
    ax[1].bar(range(3),g.net_irrigation_mm,color='#5d91b0')
    for i,v in enumerate(g.net_irrigation_mm):ax[1].text(i,v,f'{v:.1f}',ha='center',va='bottom',fontsize=8)
    ax[1].set(title='Net irrigation applied',ylabel='mm per crop season')
    ax[2].bar(range(3),g.fertiliser_N_kg_ha,color='#b6854a')
    for i,v in enumerate(g.fertiliser_N_kg_ha):ax[2].text(i,v,f'{v:.1f}',ha='center',va='bottom',fontsize=8)
    ax[2].set(title='Mineral nitrogen applied',ylabel='kg N ha$^{-1}$ per crop season')
    ax[3].bar(range(3),g.nitrate_leaching_kg_N_ha,color='#3c7da8',label='Nitrate-N')
    ax[3].bar(range(3),g.ammonium_leaching_kg_N_ha,bottom=g.nitrate_leaching_kg_N_ha,color='#8dc1b0',label='Ammonium-N')
    for i,v in enumerate(g.nitrogen_leaching_kg_N_ha):ax[3].text(i,v,f'{v:.3f}',ha='center',va='bottom',fontsize=8)
    ax[3].set(title='Profile-bottom N leaching',ylabel='kg N ha$^{-1}$ per crop season');ax[3].legend(frameon=False,fontsize=8)
    for a in ax:
        a.set_xticks(range(3),LABELS,fontsize=8);a.grid(axis='y',alpha=.2);a.set_axisbelow(True)
        a.spines[['top','right']].set_visible(False);a.margins(y=.23)
    if g.net_irrigation_mm.max()==0:ax[1].set_ylim(0,1);ax[1].text(.5,.5,'No irrigation triggered',transform=ax[1].transAxes,ha='center',fontsize=9)
    if g.fertiliser_N_kg_ha.max()==0:ax[2].set_ylim(0,1);ax[2].text(.5,.5,'No mineral N applied',transform=ax[2].transAxes,ha='center',fontsize=9)
    fig.text(.065,.21,'Target = 90% of this crop\'s open-field PP81 potential yield. Hatched yield bars did not achieve the target.',fontsize=9)
    fig.text(.065,.155,'Reported doses follow the specified controller; they are not proven minimum requirements or field recommendations.',fontsize=9)
    fig.text(.065,.105,'BK50 candidate hydraulics + SoilGrids SOC/pH + reference initial mineral N; synthetic TMY; uniform rain; 225 PV soil columns.',fontsize=8.5)
    fig.text(.065,.055,'Net irrigation assumes 100% application efficiency. Leaching crosses the 200 cm profile base; totals end with each crop run.',fontsize=8.5)
    savefig(fig,f'{crop}_Managed_Yield_Irrigation_N_Leaching')

def plot_scatter(relative):
    fig,ax=plt.subplots(figsize=(12,8.5));fig.subplots_adjust(left=.11,right=.73,top=.77,bottom=.22)
    fig.suptitle('Relative yield and ET under adaptive water–nitrogen management',x=.11,y=.96,ha='left',fontsize=17,weight='bold')
    fig.text(.11,.90,'Aachen synthetic TMY | WOFOST 8.1 | Estimated soil and initial-N scenario | Fixed-tilt PV',fontsize=11,color='#a84415')
    fig.text(.11,.85,'Each crop uses its own managed open-field baseline; input totals and target achievement are reported separately.',fontsize=9)
    pv=relative[relative.scenario_id!='open_field']
    for _,r in pv.iterrows():
        if pd.isna(r.relative_et_mm) or pd.isna(r.relative_yield_t_DM_ha):continue
        colour=CROPS[r.crop_id][1]
        ax.scatter(r.relative_et_mm,r.relative_yield_t_DM_ha,s=95,marker='o',edgecolor=colour,
            facecolor=colour if r.scenario_id==CASES[1] else 'white',linewidth=1.7,zorder=4)
        if not r.target_achieved:
            ax.annotate('†',(r.relative_et_mm,r.relative_yield_t_DM_ha),xytext=(5,5),textcoords='offset points',fontsize=12,color='#a84415')
    ax.scatter(1,1,marker='*',s=180,c='#183047',zorder=5)
    ax.axvline(1,ls='--',color='#748599',lw=1);ax.axhline(1,ls='--',color='#748599',lw=1)
    for metric,setter in [('relative_et_mm',ax.set_xlim),('relative_yield_t_DM_ha',ax.set_ylim)]:
        values=list(relative[metric].dropna())+[1.];lo,hi=min(values),max(values);pad=max(.04,(hi-lo)*.12)
        setter(max(0,lo-pad),hi+pad)
    ax.set(xlabel='Relative seasonal ET / managed open-field ET',ylabel='Relative DM yield / managed open-field DM yield')
    ax.grid(alpha=.2);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
    handles=[Line2D([],[],marker='o',ls='',color=c,label=l) for l,c in CROPS.values()]
    fig.legend(handles=handles,title='Crop',loc='upper left',bbox_to_anchor=(.76,.77),frameon=False,fontsize=9)
    handles=[Line2D([],[],marker='o',ls='',markeredgecolor='#526b80',markerfacecolor=f,label=l) for f,l in [('#526b80','Conventional PV'),('white','Semi-transparent PV')]]
    fig.legend(handles=handles,title='PV type',loc='upper left',bbox_to_anchor=(.76,.46),frameon=False,fontsize=9)
    fig.text(.77,.27,'† Common yield target\n  not achieved\n\nStar: open field (1, 1)',fontsize=9,color='#a84415')
    fig.text(.11,.145,'ET is water consumption, not irrigation. The same controller does not guarantee equal final yields under shading.',fontsize=9)
    fig.text(.11,.095,'A lower input is not an equal-yield saving when the common target is unmet. Absolute irrigation and N are in crop-specific tables.',fontsize=8.5)
    fig.text(.11,.045,'Uncalibrated scenario estimates. Ratios of area-weighted outputs; seasonal durations may differ; no marker jitter.',fontsize=8.5)
    savefig(fig,'Managed_Relative_Yield_vs_Relative_ET')

def build():
    records=[json.loads(p.read_text(encoding='utf-8')) for p in (SOURCE/'cases').glob('*/*/summary.json')]
    t=pd.DataFrame(records);keys=['crop_id','scenario_id']
    expected={(c,s) for c in CROPS for s in CASES}
    if len(t)!=18 or t.duplicated(keys).any() or set(map(tuple,t[keys].values))!=expected:raise ValueError('Need all 18 completed target-input cases')
    if t.execution_identity.nunique()!=1:raise ValueError('Mixed input manifests')
    if t.max_water_balance_residual_mm.max()>.001 or t.max_nitrogen_balance_residual_kg_N_ha.max()>.001:raise ValueError('Mass balance failed')
    if not np.allclose(t.et_mm,t.transpiration_mm+t.soil_evaporation_mm):raise ValueError('ET mismatch')
    if not np.allclose(t.nitrogen_leaching_kg_N_ha,t.nitrate_leaching_kg_N_ha+t.ammonium_leaching_kg_N_ha):raise ValueError('Leaching species mismatch')
    for crop in CROPS:
        baseline=t[(t.crop_id==crop)&(t.scenario_id=='open_field')].iloc[0]
        target=.9*baseline.potential_yield_t_DM_ha
        ix=t.crop_id==crop
        t.loc[ix,'common_yield_target_t_DM_ha']=target
        t.loc[ix,'fraction_of_common_yield_target']=t.loc[ix,'yield_t_DM_ha']/target
    t['target_achieved']=t.yield_t_DM_ha.notna()&(t.yield_t_DM_ha+1e-9>=t.common_yield_target_t_DM_ha)
    t['target_exceeds_PP81_reference']=t.potential_yield_t_DM_ha+1e-9<t.common_yield_target_t_DM_ha
    t['target_status']=np.where(t.target_achieved,'achieved',np.where(t.target_exceeds_PP81_reference,'target_exceeds_light_treatment_PP81_reference','not_achieved_under_management_rule'))
    relative=normalise(t)
    tables=DEST/'01_Tables';tables.mkdir(parents=True,exist_ok=True)
    t.to_csv(tables/'Managed_Water_Nitrogen_Comparison.csv',index=False)
    relative.to_csv(tables/'Managed_Normalised_Responses.csv',index=False)
    report_text='# Adaptive water and nitrogen inputs\n\nUncalibrated scenario estimates. Common target: 90% of each crop\'s open-field PP81 potential yield. Inputs follow a specified controller; they are not proven minimum requirements.\n\n'
    report_text+='| Crop | Light treatment | Yield (t DM/ha) | Target (t DM/ha) | Target achieved | Net irrigation (mm) | N applied (kg N/ha) | N leaching (kg N/ha) |\n|---|---|---:|---:|---|---:|---:|---:|\n'
    for _,row in t.sort_values(['crop_id','scenario_id']).iterrows():
        y='unavailable' if pd.isna(row.yield_t_DM_ha) else f'{row.yield_t_DM_ha:.3f}'
        report_text+=f'| {CROPS[row.crop_id][0]} | {row.scenario_id} | {y} | {row.common_yield_target_t_DM_ha:.3f} | {"yes" if row.target_achieved else "no"} | {row.net_irrigation_mm:.2f} | {row.fertiliser_N_kg_ha:.2f} | {row.nitrogen_leaching_kg_N_ha:.3f} |\n'
    report_text+='\nLower inputs in treatments failing the common target do not establish equal-yield savings. Seasonal ET is reported separately from irrigation. See the methods README for estimated soil, reference initial N, water-N concentrations and management assumptions.\n'
    (tables/'Managed_Results.md').write_text(report_text,encoding='utf-8')
    for crop in CROPS:plot_crop(crop,t[t.crop_id==crop])
    plot_scatter(relative)
    notes=(Path(__file__).parent/'README_Target_Inputs.md')
    if notes.exists():shutil.copy2(notes,DEST/notes.name)
    report=dict(status='passed',completed_cases=18,managed_point_seasons=int(t.points.sum()),
        potential_point_seasons=int(t.potential_point_seasons.sum()),figures=7,figure_files=21,
        target_achieved_cases=int(t.target_achieved.sum()),target_not_achieved_cases=int((~t.target_achieved).sum()),
        target_above_light_treatment_PP81_reference=int(t.target_exceeds_PP81_reference.sum()),
        zero_irrigation_baselines=list(t[(t.scenario_id=='open_field')&(t.net_irrigation_mm==0)].crop_id),
        max_water_balance_residual_mm=float(t.max_water_balance_residual_mm.max()),
        max_nitrogen_balance_residual_kg_N_ha=float(t.max_nitrogen_balance_residual_kg_N_ha.max()),
        field_validated=False,zero_denominator_policy='ratio null; absolute values and differences retained',
        visual_QA='requires final completed-figure inspection; scientific validation passed',
        inputs_are_controller_specific_not_proven_minima=True)
    (DEST/'VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (DEST/'STATUS.json').write_text(json.dumps(dict(status='complete',comparisons=18,**{k:v for k,v in report.items() if k!='status'}),ensure_ascii=False,indent=2),encoding='utf-8')
    export_file=ROOT/'08_Thesis_Results/EXPORT_STATUS.json'
    export=json.loads(export_file.read_text(encoding='utf-8'))
    export.update(adaptive_water_nitrogen_status='complete_estimated_scenario',adaptive_water_nitrogen_comparisons=18,
        adaptive_water_nitrogen_figures=7,total_figures_all_studies=int(export.get('figures',13))+7)
    export_file.write_text(json.dumps(export,ensure_ascii=False,indent=2),encoding='utf-8')
    # Collect actual summary tables/figures in the main results folders as well.
    for f in tables.glob('*.csv'):shutil.copy2(f,ROOT/'08_Thesis_Results/01_Tables'/f.name)
    for f in (DEST/'02_Figures').iterdir():shutil.copy2(f,ROOT/'08_Thesis_Results/02_Figures'/f.name)
    return report

if __name__=='__main__':build()
