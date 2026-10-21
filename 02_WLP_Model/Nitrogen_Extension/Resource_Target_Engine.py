"""Adaptive inputs on the existing WOFOST81/SNOMIN physics; explicit audit.

Only management signals are added. Crop, water and nitrogen equations are the
installed PCSE equations. Historical engines and results are not changed.
"""
from pathlib import Path
from copy import deepcopy
import json,runpy
import numpy as np
import pandas as pd

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'06_Hao_Interface_and_Rerun').is_dir())
REG=runpy.run_path(str(ROOT/'06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
REG['install']();n=REG['load_module']('nitrogen_engine')

def water_dose(sm,thickness,rd,fc,wp,rain_mm,policy):
    bottom=np.cumsum(thickness);top=bottom-thickness
    rooted=np.maximum(0.,np.minimum(bottom,rd)-top)
    capacity=float(np.sum((fc-wp)*rooted))*10
    available=float(np.sum(np.maximum(0.,sm-wp)*rooted))*10
    fraction=available/capacity if capacity>0 else 1.
    net=0.
    if fraction<policy['water_trigger_fraction_PAW']:
        net=min(policy['maximum_irrigation_mm_per_day'],
            max(0.,policy['water_refill_fraction_PAW']*capacity-available-rain_mm))
        if net<policy['minimum_irrigation_mm']:net=0.
    return net,fraction

def nitrogen_dose(available,maximum_uptake,fixation_fraction,days_since_last,applied,soybean,policy):
    cap=policy['soybean_mineral_N_cap_kg_ha'] if soybean else policy['maximum_N_per_season_kg_ha']
    buffer=policy['nitrogen_buffer_days_at_max_uptake']*maximum_uptake*(1-fixation_fraction)
    if days_since_last<policy['minimum_days_between_N_applications'] or available>=buffer*policy['nitrogen_trigger_fraction_of_buffer']:
        return 0.,buffer
    return max(0.,min(buffer-available,policy['maximum_N_per_application_kg_ha'],cap-applied)),buffer

def run_point(frame,config,data,radiation,policy):
    if config.mode!='NWLP_MLWB_SNOMIN':raise ValueError('Adaptive water/N requires NWLP/SNOMIN')
    issues=n.preflight(data,config)
    if issues:raise n.MissingNitrogenInputs(issues)
    n.base.load_pcse()
    from pcse.base import ParameterProvider
    from pcse.models import Wofost81_NWLP_MLWB_SNOMIN
    from pcse import signals
    crop,soil,site,info=n.parameters(config,data)
    if list(frame.day)!=config.weather_config().dates():raise ValueError('Weather/calendar mismatch')
    if data.get('fertilizer_events_by_crop',{}).get(config.crop_id,data['fertilizer_events']):
        raise ValueError('Fixed N events and adaptive N must not be combined implicitly')
    provider=n.base._weather_provider(frame,config.weather_config(),radiation)
    provider.description=['Aachen synthetic TMY; adaptive management; estimated soil and reference initial N']
    start,last=frame.day.iloc[0],frame.day.iloc[-1]
    spec=config.spec()
    management=[{start:dict(CropCalendar=dict(crop_name=spec['crop_name'],variety_name=spec['variety'],crop_start_date=start,
        crop_start_type='sowing',crop_end_date=last,crop_end_type='earliest',max_duration=(last-start).days+1),TimedEvents=None,StateEvents=None)}]
    layers=soil['SoilProfileDescription']['SoilLayers']
    thickness=np.array([l['Thickness'] for l in layers])
    fc=np.array([n.theta(l,soil['SoilProfileDescription']['PFFieldCapacity']) for l in layers])
    wp=np.array([n.theta(l,soil['SoilProfileDescription']['PFWiltingPoint']) for l in layers])
    actions=[];memo=dict(last_N=None,N_applied=0.)

    class Managed(Wofost81_NWLP_MLWB_SNOMIN):
        def calc_rates(self,day,drv):
            # State integration and daily management happen before rate calculation.
            # Emit each input exactly once here; do not recalculate or rewrite states.
            if self.crop is not None and day<last and not self.flag_terminate:
                dvs=self.get_variable('DVS');rd=self.get_variable('RD')
                if dvs is not None and dvs<2.:
                    water=self.soil.waterbalance;nutrient=self.soil.nutrientbalance
                    net,fraction=water_dose(np.asarray(water.states.SM),thickness,float(rd),fc,wp,float(drv.RAIN)*10,policy)
                    if net>0:
                        self._send_signal(signals.irrigate,amount=net/10/policy['irrigation_efficiency'],efficiency=policy['irrigation_efficiency'])
                    mineral=nutrient.SoilInorganicNModel().calculate_NAVAIL(nutrient.soiln_profile,nutrient.params.KSORP,
                        nutrient.states.NH4,nutrient.states.NO3,float(rd)/100,np.asarray(water.states.SM))*10000
                    since=9999 if memo['last_N'] is None else (day-memo['last_N']).days
                    dose,buffer=nitrogen_dose(mineral,float(crop['RNUPTAKEMAX']),float(crop['NFIX_FR']),since,memo['N_applied'],config.crop_id=='soybean',policy)
                    if not (0.<=dvs<=policy['N_application_end_DVS']):dose=0.
                    if dose>0:
                        self._send_signal(signals.apply_n_snomin,amount=dose,application_depth=policy['N_application_depth_cm'],
                            cnratio=0.,f_orgmat=0.,f_NH4N=policy['fertiliser_fraction_NH4_N'],f_NO3N=policy['fertiliser_fraction_NO3_N'],initial_age=0.)
                        memo.update(last_N=day,N_applied=memo['N_applied']+dose)
                    actions.append(dict(day=day,DVS=float(dvs),root_depth_cm=float(rd),root_PAW_fraction=fraction,
                        available_mineral_N_kg_ha=float(mineral),N_buffer_kg_ha=buffer,
                        net_irrigation_mm=net,gross_irrigation_mm=net/policy['irrigation_efficiency'],fertiliser_N_kg_ha=dose))
            super().calc_rates(day,drv)

    output=['DVS','LAI','TAGP','TWSO','RD','SM','TRA','EVS','RFTRA','CTRAT','CEVST','NuptakeTotal','NfixTotal',
        'WC','Flow','BOTTOMFLOW','BOTTOMFLOWT','TSR','SS','NH4','NO3','ORGMATT','NORGT','NO3LEACHCUM','NH4LEACHCUM','NDENITCUM','NLOSSCUM','NAVAIL']
    model=Managed(ParameterProvider(cropdata=crop,soildata=deepcopy(soil),sitedata=site),provider,management,
        output_vars=output,summary_vars=['NfixTotal'],terminal_vars=['TOTIRR','CTRAT','CEVST'])
    water=model.soil.waterbalance;nutrient=model.soil.nutrientbalance
    initial_water=float(np.sum(water.states.WC)+water.states.SS)
    initial_n=float(nutrient.states.NORGT+nutrient.states.NO3T+nutrient.states.NH4T)
    keys=['ammonium_bottom','nitrate_bottom','ammonium_top_native','nitrate_top_native','ammonium_last_layer_upward','nitrate_last_layer_upward']
    audit={k:0. for k in keys};byday={model.day:dict(audit)}
    while not model.flag_terminate:
        rates=n.boundary_rates(nutrient)
        model.run(days=1)
        for k,v in rates.items():audit[k]+=v
        byday[model.day]=dict(audit)
    summary=model.get_summary_output()[0];w=water.states;s=nutrient.states
    irrigation=float(w.TOTIRR)*10
    action_frame=pd.DataFrame(actions)
    planned_water=sum(a['net_irrigation_mm'] for a in actions)
    applied=float(s.RNH4AMTT+s.RNO3AMTT+s.RNORGAMTT)*10000
    if abs(irrigation-planned_water)>1e-7 or abs(applied-memo['N_applied'])>1e-7:
        raise ValueError(f'Management signal/integration mismatch: irrigation={irrigation}/{planned_water}; N={applied}/{memo["N_applied"]}')
    wres=10*(initial_water-float(np.sum(w.WC)+w.SS)+w.RAINT+w.TOTIRR-w.WTRAT-w.EVST-w.EVWT-w.TSR-w.BOTTOMFLOWT)
    deposition=float(s.RNH4DEPOSTT+s.RNO3DEPOSTT)*10000
    uptake=float(s.RNH4UPTT+s.RNO3UPTT)*10000
    final_n=float(s.NORGT+s.NH4T+s.NO3T)
    leach=audit['nitrate_bottom']+audit['ammonium_bottom']
    top_native=audit['nitrate_top_native']+audit['ammonium_top_native']
    nres=initial_n+applied+deposition-uptake-final_n-leach-top_native-float(s.NDENITCUM)
    if abs(wres)>.001 or abs(nres)>.001:raise ValueError(f'Water/N balance failure: {wres} mm, {nres} kg N/ha')
    daily=[];soil_rows=[]
    for row in model.get_output():
        flat={k:v for k,v in row.items() if not isinstance(v,(list,tuple,np.ndarray))}
        a=byday[row['day']]
        flat.update(nitrate_leaching_cumulative_kg_N_ha=a['nitrate_bottom'],ammonium_leaching_cumulative_kg_N_ha=a['ammonium_bottom'])
        daily.append(flat);top=0.
        for i,l in enumerate(layers):
            soil_rows.append(dict(day=row['day'],layer=i+1,top_cm=top,bottom_cm=top+l['Thickness'],SM_m3_m3=float(row['SM'][i]),
                water_mm=float(row['WC'][i])*10,nitrate_N_kg_ha=float(row['NO3'][i])*10000,ammonium_N_kg_ha=float(row['NH4'][i])*10000,
                upper_flow_mm_day=float(row['Flow'][i])*10,lower_flow_mm_day=float(row['Flow'][i+1])*10));top+=l['Thickness']
    mature=summary.get('DOM') is not None and float(summary['DVS'])>=1.999
    usable=mature or (spec['organ']!='grain' and summary.get('DOH') is not None)
    rf=[r.get('RFTRA') for r in daily if r.get('DVS') is not None and r['DVS']>=0 and r.get('RFTRA') is not None]
    result=dict(storage_organ_DM_kg_ha=float(summary['TWSO']),mature=mature,usable=usable,end_date=str(daily[-1]['day']),
        net_irrigation_mm=irrigation,gross_irrigation_mm=planned_water/policy['irrigation_efficiency'],
        fertiliser_N_kg_ha=applied,nitrate_leaching_kg_N_ha=audit['nitrate_bottom'],ammonium_leaching_kg_N_ha=audit['ammonium_bottom'],
        nitrogen_leaching_kg_N_ha=leach,denitrification_kg_N_ha=float(s.NDENITCUM),wet_N_input_kg_N_ha=deposition,
        soil_N_uptake_kg_N_ha=uptake,biological_N_fixation_kg_N_ha=float(summary['NfixTotal']),
        water_balance_residual_mm=wres,nitrogen_balance_residual_kg_N_ha=nres,initial_soil_N_kg_ha=initial_n,final_soil_N_kg_ha=final_n,
        top_boundary_N_export_kg_N_ha=top_native,drainage_bottom_mm=float(w.BOTTOMFLOWT)*10,runoff_mm=float(w.TSR)*10,
        transpiration_mm=float(summary['CTRAT'])*10,soil_evaporation_mm=float(summary['CEVST'])*10,
        water_stress_days=sum(float(x)<.95 for x in rf),
        N_cap_reached=bool(config.crop_id!='soybean' and applied>=policy['maximum_N_per_season_kg_ha']-1e-7))
    return dict(metrics=result,daily=pd.DataFrame(daily),soil_daily=pd.DataFrame(soil_rows),actions=action_frame,
        parameters=dict(crop=crop,soil=soil,site=site,management=management,parameter_info=info,policy=policy))
