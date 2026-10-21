"""Normalise completed crop/mode pairs to their own open-field baselines."""
from pathlib import Path
import json,math
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

CROPS={'winter_wheat':('Winter wheat','#0072B2'),'spring_barley':('Spring barley','#E69F00'),
       'grain_maize':('Grain maize','#009E73'),'potato':('Potato','#CC79A7'),
       'sugar_beet':('Sugar beet','#D55E00'),'soybean':('Soybean','#7053A3')}
MODES=('PP','WLP_MLWB')
CASES=('open_field','fixed_tilt_conventional','fixed_tilt_semi_transparent')
STEM='Summary_Relative_Yield_vs_Relative_ET'

def number(value):
    if value is None or pd.isna(value) or value=='':return None
    result=float(value)
    if not math.isfinite(result) or result<0:raise ValueError('Expected finite nonnegative model output')
    return result

def normalise(table):
    keys=['crop_id','mode','scenario_id']
    expected={(c,m,s) for c in CROPS for m in MODES for s in CASES}
    if len(table)!=36 or table.duplicated(keys).any() or set(map(tuple,table[keys].to_numpy()))!=expected:
        raise ValueError('Summary requires all 36 unique crop/mode/treatment records')
    lookup=table.set_index(keys)
    rows=[]
    for crop in CROPS:
        for mode in MODES:
            baseline=lookup.loc[(crop,mode,'open_field')]
            by,be=number(baseline.yield_t_DM_ha),number(baseline.et_mm)
            for case in CASES:
                r=lookup.loc[(crop,mode,case)]
                y,e=number(r.yield_t_DM_ha),number(r.et_mm)
                tra,evs=number(r.transpiration_mm),number(r.soil_evaporation_mm)
                if e is None or tra is None or evs is None or not math.isclose(e,tra+evs,rel_tol=1e-8,abs_tol=1e-6):
                    raise ValueError('ET must equal transpiration plus soil evaporation')
                ry=None if by is None or by<=0 or y is None else y/by
                re=None if be is None or be<=0 else e/be
                reason='valid'
                if by is None or by<=0:reason='open_field_yield_unavailable_or_zero'
                elif y is None:reason='usable_harvest_yield_unavailable'
                elif re is None:reason='open_field_ET_unavailable_or_zero'
                rows.append(dict(crop_id=crop,crop_label=CROPS[crop][0],mode=mode,scenario_id=case,
                    yield_t_DM_ha=y,et_mm=e,open_field_yield_t_DM_ha=by,open_field_et_mm=be,
                    relative_yield=ry,relative_et=re,plot_status=reason,
                    production_mode_baseline=mode,field_validated=False))
    return pd.DataFrame(rows)

def draw(data,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    valid=data[data.plot_status=='valid']
    pv=valid[valid.scenario_id!='open_field']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42,'svg.fonttype':'none'})
    fig,ax=plt.subplots(figsize=(13,8.7))
    fig.subplots_adjust(left=.105,right=.725,top=.765,bottom=.205)
    fig.suptitle('Relative yield versus relative seasonal ET',x=.105,y=.965,ha='left',fontsize=20,weight='bold',color='#183047')
    fig.text(.105,.905,'Aachen | WOFOST 7.3 | Fixed-tilt PV | Six crops | PP and layered WLP',fontsize=11,color='#35566f')
    fig.text(.105,.86,'Each crop and production mode is normalised to its own open-field baseline.',fontsize=10,color='#526b80')
    for crop,(_,colour) in CROPS.items():
        for mode in MODES:
            for case in CASES[1:]:
                subset=pv[(pv.crop_id==crop)&(pv['mode']==mode)&(pv.scenario_id==case)]
                if subset.empty:continue
                r=subset.iloc[0]
                ax.scatter(r.relative_et,r.relative_yield,s=85,marker='o' if mode=='PP' else '^',
                    facecolors=colour if case=='fixed_tilt_conventional' else 'white',edgecolors=colour,
                    linewidths=1.8,zorder=4 if case=='fixed_tilt_semi_transparent' else 3)
    for orientation in ('h','v'):
        (ax.axhline if orientation=='h' else ax.axvline)(1,color='#728597',ls=(0,(5,4)),lw=1.1,zorder=2)
    baselines=valid[valid.scenario_id=='open_field']
    if len(baselines):
        ax.scatter([1],[1],marker='*',s=210,c='#183047',edgecolors='white',linewidths=.7,zorder=6)
        ax.annotate('Open-field reference\n(1, 1)',xy=(1,1),xycoords='data',xytext=(.98,.95),textcoords='axes fraction',
                    ha='right',va='top',fontsize=9,color='#35566f',arrowprops=dict(arrowstyle='-',color='#728597',lw=.9))
    for values,setter in ((list(pv.relative_et)+[1.],ax.set_xlim),(list(pv.relative_yield)+[1.],ax.set_ylim)):
        lo,hi=min(values),max(values);padding=max(.035,(hi-lo)*.13)
        setter(max(0,lo-padding),hi+padding)
    ax.set_xlabel(r'Relative seasonal evapotranspiration, ET / ET$_{\mathrm{open\ field}}$',labelpad=13)
    ax.set_ylabel(r'Relative dry-matter yield, Y / Y$_{\mathrm{open\ field}}$',labelpad=10)
    ax.grid(color='#e2e8f0',lw=.7);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
    crop_handles=[Line2D([],[],marker='o',ls='',markersize=7,color=colour,label=label) for label,colour in CROPS.values()]
    mode_handles=[Line2D([],[],marker=marker,ls='',markersize=7,color='#526b80',label=label) for marker,label in [('o','PP'),('^','WLP')]]
    type_handles=[Line2D([],[],marker='o',ls='',markersize=7,markerfacecolor=fill,markeredgecolor='#526b80',markeredgewidth=1.5,label=label)
                  for fill,label in [('#526b80','Conventional PV'),('white','Semi-transparent PV')]]
    fig.legend(handles=crop_handles,title='Crop · colour',loc='upper left',bbox_to_anchor=(.755,.78),frameon=False,fontsize=9.5,title_fontsize=10)
    fig.legend(handles=mode_handles,title='Production mode · shape',loc='upper left',bbox_to_anchor=(.755,.50),frameon=False,fontsize=9.5,title_fontsize=10)
    fig.legend(handles=type_handles,title='PV type · fill',loc='upper left',bbox_to_anchor=(.755,.34),frameon=False,fontsize=9.5,title_fontsize=10)
    fig.text(.77,.17,'1.0 = no change\n0.8 = 20% lower\n1.1 = 10% higher',fontsize=9,color='#526b80',linespacing=1.5)
    excluded=24-len(pv)
    fig.text(.105,.125,f'{len(pv)} PV points shown; {len(baselines)} valid open-field baselines overlap at (1, 1).'+
             (f' {excluded} PV case(s) excluded; see ratio table.' if excluded else ''),fontsize=9,color='#526b80')
    fig.text(.105,.084,'Uncalibrated synthetic-TMY simulations. ET is not irrigation requirement; crop-specific data tables retain absolute values.',fontsize=8.5,color='#526b80')
    fig.text(.105,.045,"ET is integrated to each run's end; duration changes contribute to the ratios. Markers may overlap; no jitter applied.",fontsize=8.3,color='#526b80')
    files=[]
    for ext in ('png','pdf','svg'):
        p=directory/f'{STEM}.{ext}';fig.savefig(p,dpi=240,facecolor='white');files.append(p)
    plt.close(fig)
    return files

def build(table,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    ratios=normalise(table)
    ratios.to_csv(output/'normalised_yield_ET.csv',index=False)
    draw(ratios,output/'figures')
    report=dict(source_records=36,expected_PV_points=24,plotted_PV_points=int(((ratios.scenario_id!='open_field')&(ratios.plot_status=='valid')).sum()),
        valid_open_field_baselines=int(((ratios.scenario_id=='open_field')&(ratios.plot_status=='valid')).sum()),
        denominator='open_field of the same crop_id and mode',jitter_applied=False,
        missing_or_unusable_yields='retained as missing; omitted from scatter, never imputed')
    (output/'normalised_yield_ET_validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return ratios
