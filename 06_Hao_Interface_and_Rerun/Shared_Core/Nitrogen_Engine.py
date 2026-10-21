"""Sourced WOFOST81/SNOMIN extension; missing field inputs never become invented zeros.
: , . 
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict,dataclass
from datetime import date
from pathlib import Path
import json,math,hashlib
import numpy as np
import pandas as pd
import yaml
import crop_engine as base

ROOT=base.ROOT
ENGINE_SHA256=base.sha256(__file__)
INPUTS=ROOT/'04_Soil_and_Python/Nitrogen_Inputs'
DEFAULT_FIELD='04_Soil_and_Python/Nitrogen_Inputs/Aachen_Field_Inputs.json'
REFERENCE='04_Soil_and_Python/Nitrogen_Inputs/Published_Reference.json'
MODELS={'PP81':'Wofost81_PP','WLP81':'Wofost81_WLP_MLWB','NWLP_MLWB_SNOMIN':'Wofost81_NWLP_MLWB_SNOMIN'}
CROP_FILES={'wheat':'wheat.yaml','barley':'barley.yaml','maize':'maize.yaml','potato':'potato.yaml','sugarbeet':'sugarbeet.yaml','soybean':'soybean.yaml'}
N_SITE=['A0SOM','CNRatioBio','FASDIS','KDENIT_REF','KNIT_REF','KSORP','MRCDIS','NH4ConcR','NO3ConcR','WFPS_CRIT','NH4I','NO3I']
W_SITE=['WAV','CO2','IFUNRN','NOTINF','SSI','SSMAX','SMLIM']

class MissingNitrogenInputs(ValueError):
    def __init__(self,issues):
        self.issues=issues
        super().__init__('Missing/invalid sourced nitrogen inputs / : '+'; '.join(issues))

@dataclass(frozen=True)
class NitrogenConfig:
    crop_id:str='winter_wheat'
    mode:str='NWLP_MLWB_SNOMIN'
    harvest_year:int=2002
    nitrogen_inputs:str=DEFAULT_FIELD
    accept_reference_scenario:bool=False
    accept_demo_assumptions:bool=False

    def spec(self):
        if self.crop_id not in base.crop_catalog():raise ValueError('Unknown crop / ')
        if self.mode not in MODELS:raise ValueError('Use NWLP_MLWB_SNOMIN, PP81 or WLP81')
        return deepcopy(base.crop_catalog()[self.crop_id])

    def weather_config(self):return self.base_config().weather_config()

    def base_config(self):
        return base.ModelConfig(crop_id=self.crop_id,harvest_year=self.harvest_year,
            accept_demo_assumptions=self.accept_demo_assumptions)

def load_inputs(config):
    path=Path(config.nitrogen_inputs)
    if not path.is_absolute():path=ROOT/path
    data=json.loads(path.read_text(encoding='utf-8'))
    data['_input_sha256']=base.sha256(path)
    return data

def preflight(data,config):
    config.spec();issues=[]
    if not config.accept_demo_assumptions:issues.append('Explicit TMY/weather demonstration acknowledgement required / TMY')
    if data.get('scenario_kind') not in ['field','reference_only']:issues.append('scenario_kind must be field/reference_only')
    if data.get('scenario_kind')=='reference_only' and not config.accept_reference_scenario:
        issues.append('Reference-only inputs require accept_reference_scenario=True / ')
    if data.get('scenario_kind')=='field':
        for key in ['field_location','NO3I','NH4I','FSOMI','CNRatioSOMI','Soil_pH','fertilizer_events',
                    'NH4ConcR','NO3ConcR','initial_water','CO2']:
            if not data.get('field_sources',{}).get(key):issues.append('field_sources.'+key+' / Missing field-parameter source')
    for item in data.get('missing_parameters',[]):
        if item.get('status')=='missing':issues.append(item['parameter'])
    profile=data.get('SoilProfileDescription',{});layers=profile.get('SoilLayers',[])
    if not layers:issues.append('SoilLayers')
    if profile.get('GroundWater'):issues.append('Groundwater influence is not implemented in bundled MLWB')
    for i,layer in enumerate(layers):
        for key in ['FSOMI','CNRatioSOMI','Soil_pH','Thickness','RHOD','CRAIRC']:
            value=layer.get(key)
            if value is None or not isinstance(value,(float,int)) or not math.isfinite(value):issues.append(f'SoilLayers[{i}].{key}')
        for key in ['SMfromPF','CONDfromPF']:
            value=layer.get(key)
            if value is None or len(value)<4 or len(value)%2 or not np.isfinite(np.asarray(value,float)).all():issues.append(f'SoilLayers[{i}].{key}')
        if layer.get('CNRatioSOMI') is not None and layer['CNRatioSOMI']<=0:issues.append(f'CNRatioSOMI[{i}] must be positive')
        if layer.get('FSOMI') is not None and not 0<=layer['FSOMI']<=1:issues.append(f'FSOMI[{i}] must be a mass fraction')
        if layer.get('Soil_pH') is not None and not 0<layer['Soil_pH']<14:issues.append(f'Soil_pH[{i}] out of range')
    site=data.get('site',{})
    for key in W_SITE+N_SITE:
        value=site.get(key)
        if value is None:issues.append('site.'+key);continue
        arr=np.asarray(value,float)
        if not np.isfinite(arr).all():issues.append('nonfinite site.'+key)
        if key in ['NH4I','NO3I'] and (arr.shape!=(len(layers),) or (arr<0).any()):issues.append(key+' requires one nonnegative kg N/ha amount per source layer')
    if not data.get('parameter_provenance'):issues.append('parameter_provenance / ')
    limit=data.get('max_rootable_depth_cm')
    if limit is None or limit<=0:issues.append('max_rootable_depth_cm')
    events=data.get('fertilizer_events_by_crop',{}).get(config.crop_id,data.get('fertilizer_events'))
    if events is None:issues.append('fertilizer_events: unknown is not an unfertilised treatment / ')
    elif not isinstance(events,list):issues.append('fertilizer_events must be an explicitly sourced list')
    else:
        dates=[]
        for event in events:
            for key in ['date','amount','application_depth','cnratio','f_orgmat','f_NH4N','f_NO3N','initial_age','source']:
                if event.get(key) is None:issues.append('fertilizer_event.'+key)
            if event.get('date') is not None:dates.append(str(event['date']))
            if any(event.get(k) is None for k in ['amount','application_depth','cnratio','f_orgmat','f_NH4N','f_NO3N','initial_age']):continue
            nums=[event[k] for k in ['amount','application_depth','cnratio','f_orgmat','f_NH4N','f_NO3N','initial_age']]
            if not np.isfinite(nums).all() or min(nums)<0:issues.append('invalid fertilizer values')
            if any(event[k]>1 for k in ['f_orgmat','f_NH4N','f_NO3N']):issues.append('fertilizer fractions outside [0,1]')
            if event['f_NH4N']+event['f_NO3N']>1:issues.append('mineral fertilizer fractions exceed one')
            if event['f_orgmat']>0 and event['cnratio']<=0:issues.append('organic amendment requires positive C:N')
        if len(dates)!=len(set(dates)):issues.append('Combine same-day amendments explicitly; bundled SNOMIN overwrites their mineral rates')
    return list(dict.fromkeys(issues))

def theta(layer,pf):
    arr=np.array(layer['SMfromPF']).reshape(-1,2)
    return float(np.interp(pf,arr[:,0],arr[:,1]))

def boundary_rates(nutrient):
    """Audit existing PCSE fluxes without changing its transport equations.
    PCSE 6.0.13's R*OUT[-1] includes internal upward export from the last layer.
    Its top boundary also exports dissolved N with negative surface water flow.
    Keep these separate; neither is automatically profile-bottom leaching.
    """
    s,r,p=nutrient.states,nutrient.rates,nutrient.params
    flow=nutrient.get_water_flow_rates(nutrient.kiosk)
    sm=nutrient.get_soil_moisture_content(nutrient.kiosk)
    dz=np.asarray([l.Thickness_m for l in nutrient.soiln_profile])
    rho=np.asarray([l.RHOD_kg_per_m3 for l in nutrient.soiln_profile])
    nh4=s.NH4-r.RNH4UP+r.RNH4AM+r.RNH4MIN+r.RNH4DEPOS-r.RNH4NITR
    no3=s.NO3-r.RNO3UP+r.RNO3AM+r.RNO3NITR+r.RNO3DEPOS-r.RNO3DENITR
    concentrations=[nh4/((p.KSORP*rho+sm)*dz),no3/(sm*dz)]
    values={}
    for label,c,outs in zip(['ammonium','nitrate'],concentrations,[r.RNH4OUT,r.RNO3OUT]):
        internal_up=max(-float(flow[-2]),0.)*float(c[-1])
        bottom=float(outs[-1])-internal_up
        top=max(-float(flow[0]),0.)*float(c[0])
        if bottom < -1e-10:raise ValueError('Unexpected upward bottom N input; inspect model boundary assumptions')
        values[label+'_bottom']=max(0.,bottom)*10000
        values[label+'_top_native']=top*10000
        values[label+'_last_layer_upward']=internal_up*10000
    return values

def parameters(config,data):
    spec=config.spec();path=INPUTS/'Crop_Parameters_81'/CROP_FILES[spec['crop_name']]
    source=yaml.safe_load(path.read_text(encoding='utf-8'))
    variety=source['CropParameters']['Varieties'][spec['variety']]
    crop={k:deepcopy(v[0]) for k,v in variety.items() if k!='Metadata'}
    profile=deepcopy(data['SoilProfileDescription']);source_layers=profile['SoilLayers']
    limit=min(float(crop['RDMCR']),float(data['max_rootable_depth_cm']),sum(l['Thickness'] for l in source_layers))
    if limit<crop['RDI']:raise ValueError('Root limit shallower than initial root depth')
    crop['RDMCR']=limit;crop['IAIRDU']=int(crop.get('IAIRDU',0))
    layers=[];no3=[];nh4=[];top=0.;mapping=[]
    for idx,layer in enumerate(source_layers):
        bottom=top+layer['Thickness']
        anchors=sorted(set([top,bottom]+[x for x in [10.,limit] if top<x<bottom]))
        for a,b in zip(anchors,anchors[1:]):
            count=math.ceil((b-a)/20.)
            for i in range(count):
                lo=a+(b-a)*i/count;hi=a+(b-a)*(i+1)/count
                if hi-lo<5-1e-7:raise ValueError('Refinement would create layer thinner than PCSE minimum 5 cm')
                child=deepcopy(layer);child.update(Thickness=hi-lo,SoilID=f'N_source{idx+1}_{lo:g}_{hi:g}cm');layers.append(child)
                fraction=(hi-lo)/layer['Thickness']
                no3.append(data['site']['NO3I'][idx]*fraction);nh4.append(data['site']['NH4I'][idx]*fraction)
                mapping.append(dict(source_layer=idx+1,top_cm=lo,bottom_cm=hi,source_fraction=fraction))
        top=bottom
    profile['SoilLayers']=layers
    first=layers[0];fc=theta(first,profile['PFFieldCapacity']);wp=theta(first,profile['PFWiltingPoint'])
    soil=dict(SMW=wp,SMFCF=fc,SM0=theta(first,-1),CRAIRC=first['CRAIRC'],RDMSOL=limit,SoilProfileDescription=profile)
    base.load_pcse()
    from pcse.input import WOFOST81SiteDataProvider_SNOMIN
    site=dict(WOFOST81SiteDataProvider_SNOMIN(**dict(data['site'],NO3I=no3,NH4I=nh4)))
    for key,arr in [('NO3I',no3),('NH4I',nh4)]:
        if not math.isclose(sum(arr),sum(data['site'][key]),abs_tol=1e-9):raise ValueError('Initial N not conserved during refinement')
    return crop,soil,site,dict(variety=spec['variety'],crop_source_sha256=base.sha256(path),
        source_root_limit_cm=float(variety['RDMCR'][0]),applied_root_limit_cm=limit,NFIX_FR=crop['NFIX_FR'],layer_mapping=mapping)

def run_point(frame,config,data,*,radiation=None,effective_rain=None):
    base.load_pcse()
    from pcse.base import ParameterProvider
    from pcse import models
    issues=preflight(data,config)
    if issues:raise MissingNitrogenInputs(issues)
    crop,soil,site,info=parameters(config,data);wc=config.weather_config();spec=config.spec()
    if list(frame.day)!=wc.dates():raise ValueError('Weather dates must match crop calendar exactly')
    actual=frame.copy(deep=True)
    if effective_rain is not None:
        rain=np.asarray(effective_rain,float)
        if rain.shape!=(len(frame),) or not np.isfinite(rain).all() or (rain<0).any():raise ValueError('Invalid effective rainfall')
        actual['RAIN_mm_day']=rain
    provider=base._weather_provider(actual,wc,actual.IRRAD if radiation is None else radiation)
    provider.description=['Aachen synthetic TMY; WOFOST81 sourced nitrogen reference or strict field inputs']
    start,last=wc.dates()[0],wc.dates()[-1]
    events=deepcopy(data.get('fertilizer_events_by_crop',{}).get(config.crop_id,data['fertilizer_events']))
    table=[]
    for event in events:
        day=date.fromisoformat(str(event['date']))
        if not start<=day<=last:raise ValueError('Fertilizer date outside the simulated crop period; do not silently drop it')
        table.append({day:{k:v for k,v in event.items() if k not in ['date','source']}})
    timed=[dict(event_signal='apply_n_snomin',name='Sourced fertilizer events / ',comment='amount kg amendment/ha; mineral fractions kg N/kg amendment',events_table=table)] if table else None
    management=[{start:dict(CropCalendar=dict(crop_name=spec['crop_name'],variety_name=spec['variety'],crop_start_date=start,
        crop_start_type='sowing',crop_end_date=last,crop_end_type='earliest',max_duration=(last-start).days+1),TimedEvents=timed,StateEvents=None)}]
    nmode=config.mode=='NWLP_MLWB_SNOMIN';layered=config.mode!='PP81'
    output=['DVS','LAI','TAGP','TWSO','RD','SM','TRA','EVS','RFTRA','CTRAT','CEVST','NuptakeTotal','NfixTotal']
    terminal=['CTRAT','CEVST','NuptakeTotal','NfixTotal','DVS','RD','TWSO']
    if layered:
        output+=['WC','Flow','BOTTOMFLOW','BOTTOMFLOWT','TSR','SS']
        terminal+=['WC','SS','RAINT','TOTIRR','BOTTOMFLOWT','TSR','EVWT']
    if nmode:
        output+=['NH4','NO3','ORGMATT','NORGT','NO3LEACHCUM','NH4LEACHCUM','NDENITCUM','NLOSSCUM','NAVAIL']
        terminal+=['NH4','NO3','NORGT','NO3LEACHCUM','NH4LEACHCUM','NDENITCUM','NLOSSCUM']
    model=getattr(models,MODELS[config.mode])(ParameterProvider(cropdata=crop,soildata=deepcopy(soil),sitedata=site),provider,management,
        output_vars=output,terminal_vars=terminal,summary_vars=['NfixTotal'])
    water=model.soil.waterbalance if layered else None
    initial_water=None if not layered else float(np.sum(water.states.WC)+water.states.SS)
    nutrient=model.soil.nutrientbalance if nmode else None
    initial_n=None if not nmode else float(nutrient.states.NORGT+nutrient.states.NO3T+nutrient.states.NH4T)
    audit={key:0. for key in ['ammonium_bottom','nitrate_bottom','ammonium_top_native','nitrate_top_native','ammonium_last_layer_upward','nitrate_last_layer_upward']}
    audit_by_day={model.day:dict(audit)}
    while not model.flag_terminate:
        rates=boundary_rates(nutrient) if nmode else None
        model.run(days=1)
        if nmode:
            for key,value in rates.items():audit[key]+=value
            audit_by_day[model.day]=dict(audit)
    raw=model.get_output();summary=model.get_summary_output()[0];term=model.get_terminal_output()
    nitrogen={};water_residual=None
    if layered:
        w=water.states
        water_residual=10*(initial_water-float(np.sum(w.WC)+w.SS)+w.RAINT+w.TOTIRR-w.WTRAT-w.EVST-w.EVWT-w.TSR-w.BOTTOMFLOWT)
        if abs(water_residual)>0.001:raise ValueError(f'Water balance residual exceeds 0.001 mm: {water_residual}')
    if nmode:
        s=nutrient.states
        applied=float(s.RNH4AMTT+s.RNO3AMTT+s.RNORGAMTT)*10000
        deposition=float(s.RNH4DEPOSTT+s.RNO3DEPOSTT)*10000
        uptake=float(s.RNH4UPTT+s.RNO3UPTT)*10000
        final=float(s.NORGT+s.NH4T+s.NO3T)
        leach=audit['nitrate_bottom']+audit['ammonium_bottom']
        top_native=audit['nitrate_top_native']+audit['ammonium_top_native']
        n_residual=initial_n+applied+deposition-uptake-final-leach-top_native-float(s.NDENITCUM)
        if abs(n_residual)>0.001:
            debug=dict(initial_n=initial_n,applied=applied,deposition=deposition,uptake=uptake,final=final,leach=leach,denit=float(s.NDENITCUM),residual=n_residual,
                organic_balance=float(nutrient._NORGI.sum()-s.NORG.sum()+s.RNORGAMTT-s.RNORGDISTT)*10000,
                ammonium_balance=float(nutrient._NH4I.sum()-s.NH4.sum()+s.RNH4AMTT+s.RNH4INTT+s.RNH4MINTT+s.RNH4DEPOSTT-s.RNH4NITRTT-s.RNH4OUTTT-s.RNH4UPTT)*10000,
                nitrate_balance=float(nutrient._NO3I.sum()-s.NO3.sum()+s.RNO3AMTT+s.RNO3NITRTT+s.RNO3INTT+s.RNO3DEPOSTT-s.RNO3DENITRTT-s.RNO3OUTTT-s.RNO3UPTT)*10000,
                boundary_flux_difference=float(s.RNH4OUTTT+s.RNO3OUTTT-s.RNH4INTT-s.RNO3INTT)*10000)
            raise ValueError('N balance failure / : '+json.dumps(debug))
        nitrogen=dict(nitrate_leaching_kg_N_ha=audit['nitrate_bottom'],ammonium_leaching_kg_N_ha=audit['ammonium_bottom'],
            nitrogen_leaching_kg_N_ha=leach,denitrification_kg_N_ha=float(s.NDENITCUM),
            model_N_loss_kg_N_ha=float(s.NLOSSCUM),nitrogen_balance_residual_kg_N_ha=n_residual,
            pcse_native_nitrate_last_layer_out_kg_N_ha=float(s.NO3LEACHCUM),
            pcse_native_ammonium_last_layer_out_kg_N_ha=float(s.NH4LEACHCUM),
            pcse_native_top_boundary_N_export_kg_N_ha=top_native,
            last_layer_internal_upward_N_kg_N_ha=audit['nitrate_last_layer_upward']+audit['ammonium_last_layer_upward'],
            initial_soil_total_N_kg_N_ha=initial_n,final_soil_total_N_kg_N_ha=final,
            fertilizer_N_applied_kg_N_ha=applied,wet_N_input_kg_N_ha=deposition,soil_N_uptake_kg_N_ha=uptake)
    daily=[];layer_rows=[];previous_no3=previous_nh4=0.
    for row in raw:
        flat={k:v for k,v in row.items() if not isinstance(v,(list,tuple,np.ndarray))}
        if nmode:
            counters=audit_by_day[row['day']]
            flat['nitrate_leaching_kg_N_ha_day']=counters['nitrate_bottom']-previous_no3
            flat['ammonium_leaching_kg_N_ha_day']=counters['ammonium_bottom']-previous_nh4
            flat['nitrate_leaching_cumulative_kg_N_ha']=counters['nitrate_bottom']
            flat['ammonium_leaching_cumulative_kg_N_ha']=counters['ammonium_bottom']
            previous_no3=counters['nitrate_bottom'];previous_nh4=counters['ammonium_bottom']
        if layered:
            top=0.
            for i,layer in enumerate(soil['SoilProfileDescription']['SoilLayers']):
                item=dict(day=row['day'],layer=i+1,top_cm=top,bottom_cm=top+layer['Thickness'],
                    SM_m3_m3=float(row['SM'][i]),water_mm=float(row['WC'][i])*10,
                    upper_flow_mm_day=float(row['Flow'][i])*10,lower_flow_mm_day=float(row['Flow'][i+1])*10)
                if nmode:item.update(nitrate_N_kg_ha=float(row['NO3'][i])*10000,ammonium_N_kg_ha=float(row['NH4'][i])*10000)
                layer_rows.append(item);top+=layer['Thickness']
        daily.append(flat)
    mature=summary.get('DOM') is not None and float(summary['DVS'])>=1.999
    harvested=summary.get('DOH') is not None
    usable=mature or (spec['organ']!='grain' and harvested)
    water_metrics=dict(transpiration_mm=float(summary['CTRAT'])*10,soil_evaporation_mm=float(summary['CEVST'])*10,
        drainage_bottom_mm=None if not layered else float(water.states.BOTTOMFLOWT)*10,
        runoff_mm=None if not layered else float(water.states.TSR)*10,water_balance_residual_mm=water_residual)
    return dict(daily=pd.DataFrame(daily),soil_daily=pd.DataFrame(layer_rows),summary=summary,terminal=term,
        soil=soil,site=site,management=management,crop_parameters=crop,parameter_info=info,
        mature=mature,usable=usable,storage_organ_DM_kg_ha=float(summary['TWSO']),
        biological_N_fixation_kg_N_ha=float(summary['NfixTotal']),
        **water_metrics,**nitrogen)

def evaluate(config,*,radiation=None,scenario_id='natural_light',provenance=None,grid=None,baseline=None,spatial_mode='pointwise'):
    data=load_inputs(config);issues=preflight(data,config)
    if issues:raise MissingNitrogenInputs(issues)
    frame,weather=base.prepare_weather(config.base_config());grid=grid or base.GroundGrid()
    area=float(grid.points().cell_area_m2.sum())
    if spatial_mode!='pointwise':raise ValueError('Nitrogen mode requires pointwise soil columns; no average-radiation shortcut')
    if scenario_id=='natural_light':
        if radiation is not None:raise ValueError('Natural light must use EPW radiation')
        jobs=[('whole_plot',area,frame.IRRAD.to_numpy(),None)]
    else:
        if radiation is None or not provenance:raise ValueError('APV needs complete daily-by-point radiation and provenance')
        if isinstance(radiation,(str,Path)):radiation=pd.read_csv(radiation)
        selected=base.validate_radiation(frame,radiation,scenario_id,grid);jobs=[]
        for pid,g in selected.groupby('point_id',sort=True):
            order=g.set_index('day').reindex(frame.day)
            jobs.append((pid,float(g.cell_area_m2.iloc[0]),order.total_Wh_m2_day.to_numpy(float)*3600,
                order.effective_rain_mm_day.to_numpy(float) if 'effective_rain_mm_day' in order else None))
    results=[];daily=[];layers=[];last=None
    for pid,weight,light,rain in jobs:
        result=run_point(frame,config,data,radiation=light,effective_rain=rain);last=result
        row={k:v for k,v in result.items() if k not in ['daily','soil_daily','summary','terminal','soil','site','management','crop_parameters','parameter_info']}
        row.update(point_id=pid,cell_area_m2=weight,end_date=str(result['daily'].day.iloc[-1]));results.append(row)
        for target,key in [(daily,'daily'),(layers,'soil_daily')]:
            df=result[key].copy()
            if not df.empty:df.insert(0,'point_id',pid);target.append(df)
    table=pd.DataFrame(results)
    def avg(key):
        return None if key not in table or table[key].isna().any() else float(np.average(table[key],weights=table.cell_area_m2))
    identity=base.fingerprint(dict(config=asdict(config),input_sha256=data['_input_sha256'],crop_sha256=last['parameter_info']['crop_source_sha256'],
        engine_sha256=ENGINE_SHA256,grid=asdict(grid),weather_sha=base.fingerprint(frame.to_json(date_format='iso'))))
    usable=bool(table.usable.all());value=avg('storage_organ_DM_kg_ha');reference=data['scenario_kind']=='reference_only'
    payload=dict(schema_version='hao-crop-water-nitrogen-v1',crop_id=config.crop_id,crop_label=config.spec()['label'],mode=config.mode,
        model=MODELS[config.mode],model_version='8.1',pcse_version='6.0.13',scenario_id=scenario_id,
        nitrogen_input_scenario=data['scenario_id'],scenario_kind=data['scenario_kind'],field_validated=False,
        status=('reference_only_' if reference else 'uncalibrated_field_')+('mature' if usable else 'not_mature_by_cutoff'),
        eligible_for_field_optimization=False if reference else usable,
        all_points_mature=bool(table.mature.all()),all_points_usable=usable,
        storage_organ_DM_kg_ha=value,yield_kg_DM_ha=value if usable else None,common_planted_area_m2=area,
        config=asdict(config),comparison_fingerprint=identity,relative_yield_to_natural=None,
        leaching_boundary_depth_cm=sum(l['Thickness'] for l in last['soil']['SoilProfileDescription']['SoilLayers']),
        leaching_boundary_definition='Bottom of entire soil profile, not instantaneous rooting depth / , ',
        weather_provenance=weather,radiation_provenance=provenance,nitrogen_input_sha256=data['_input_sha256'],
        executed_engine_sha256=ENGINE_SHA256,
        crop_parameter_info=last['parameter_info'],
        limitations=['Reference inputs do not establish Aachen field nitrogen losses. / Aachen. ',
          'Synthetic TMY and liquid rain only; no snowmelt. / , . ',
          'No automatic panel runoff redistribution or lateral soil exchange. / . ',
          'SNOMIN model_N_loss includes leaching plus denitrification, not all environmental N loss. / , . ',
          'Native SNOMIN last-layer outflow includes internal upward movement; reported leaching excludes that component. / , . ',
          'Native top-boundary N export is reported separately for model accounting; not interpreted as measured runoff or volatilisation. / , . ',
          'Soybean fixation uses sourced NFIX_FR; not a mechanistic nodule model. / SoybeanNFIX_FR, . ',
          'WOFOST81 cannot be attributed as a nitrogen treatment against historical WOFOST73 output. / WOFOST73. '])
    for key in ['transpiration_mm','soil_evaporation_mm','drainage_bottom_mm','runoff_mm','nitrate_leaching_kg_N_ha','ammonium_leaching_kg_N_ha',
        'nitrogen_leaching_kg_N_ha','denitrification_kg_N_ha','model_N_loss_kg_N_ha','fertilizer_N_applied_kg_N_ha',
        'wet_N_input_kg_N_ha','soil_N_uptake_kg_N_ha','biological_N_fixation_kg_N_ha',
        'pcse_native_nitrate_last_layer_out_kg_N_ha','pcse_native_ammonium_last_layer_out_kg_N_ha',
        'pcse_native_top_boundary_N_export_kg_N_ha','last_layer_internal_upward_N_kg_N_ha']:
        payload[key]=avg(key)
    payload['water_balance_max_abs_residual_mm']=None if config.mode=='PP81' else float(table.water_balance_residual_mm.abs().max())
    payload['nitrogen_balance_max_abs_residual_kg_N_ha']=None if config.mode!='NWLP_MLWB_SNOMIN' else float(table.nitrogen_balance_residual_kg_N_ha.abs().max())
    if baseline is not None:
        if baseline.get('scenario_id')!='natural_light' or baseline.get('comparison_fingerprint')!=identity:raise ValueError('Baseline must match crop, version, mode, management, soil, N, weather and grid')
        if usable and baseline.get('yield_kg_DM_ha'):payload['relative_yield_to_natural']=value/baseline['yield_kg_DM_ha']
    folder=base.new_run(f'WOFOST81_{config.mode}/{config.crop_id}')
    payload['run_id']=folder.name
    table.to_csv(folder/'Point_Summary.csv',index=False,encoding='utf-8-sig')
    pd.concat(daily,ignore_index=True).to_csv(folder/'Daily_Water_Nitrogen.csv',index=False,encoding='utf-8-sig')
    if layers:pd.concat(layers,ignore_index=True).to_csv(folder/'Daily_Soil_Nitrogen.csv',index=False,encoding='utf-8-sig')
    if scenario_id!='natural_light':selected.to_csv(folder/'Daily_Point_Radiation.csv',index=False,encoding='utf-8-sig')
    frame.to_csv(folder/'Input_Weather.csv',index=False,encoding='utf-8-sig')
    base.save_json(folder/'Hao_Crop_Water_Nitrogen.json',payload)
    base.save_json(folder/'Configuration_and_Parameters.json',dict(config=asdict(config),inputs=data,
        crop=last['crop_parameters'],soil=last['soil'],site=last['site'],management=last['management'],parameter_info=last['parameter_info']))
    return payload,folder
