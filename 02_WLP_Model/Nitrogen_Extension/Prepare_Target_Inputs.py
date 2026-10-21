"""Build an explicit estimated-soil scenario; never alter the strict field template."""
from pathlib import Path
from copy import deepcopy
import hashlib,json,runpy
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'06_Hao_Interface_and_Rerun').is_dir())
INPUTS=ROOT/'04_Soil_and_Python/Nitrogen_Inputs'
TARGET=INPUTS/'Aachen_BK50_SoilGrids_Target.json'

def build():
    reference=json.loads((INPUTS/'Published_Reference.json').read_text(encoding='utf-8'))
    water=json.loads((ROOT/'04_Soil_and_Python/Soil_Inputs/Soil_Profile_Demo.json').read_text(encoding='utf-8'))
    raw=json.loads((INPUTS/'Source_Records/SoilGrids_Aachen_C_N_pH.json').read_text(encoding='utf-8'))
    properties={x['name']:x for x in raw['properties']['layers']}
    def value(name,depth):
        prop=properties[name]
        for d in prop['depths']:
            if d['range']['top_depth']<=depth<d['range']['bottom_depth']:
                return d['values']['mean']/prop['unit_measure']['d_factor']
        raise ValueError('SoilGrids does not cover requested depth')
    data=deepcopy(reference)
    data.update(scenario_id='aachen_BK50_SoilGrids_estimated_initial_N35_target_management',
        scenario_kind='reference_only',field_validated=False,
        description='BK50 candidate hydraulic profile + SoilGrids predicted SOC/pH + published biochemical and mineral-N assumptions. Adaptive water/N management; not a field reconstruction.',
        max_rootable_depth_cm=water['demonstration_soil_root_limit_cm'])
    profile=deepcopy(water['SoilProfileDescription']);parents=profile['SoilLayers']
    boundaries={0.,5.,15.,25.,30.,40.,60.,100.,200.}
    top=0.
    for layer in parents:top+=layer['Thickness'];boundaries.add(top)
    edges=sorted(boundaries);layers=[];no3=[];nh4=[]
    for lo,hi in zip(edges,edges[1:]):
        middle=(lo+hi)/2;top=0.
        for parent in parents:
            if top<=middle<top+parent['Thickness']:break
            top+=parent['Thickness']
        layer=deepcopy(parent)
        layer.update(Thickness=hi-lo,SoilID=f'BK50_SoilGrids_{lo:g}_{hi:g}cm',
            FSOMI=value('soc',middle)/1000/.58,Soil_pH=value('phh2o',middle),
            CNRatioSOMI=17. if middle<25 else 25.)
        layers.append(layer)
        # Explicit published reference: 30 NO3-N + 5 NH4-N in 0–25 cm;
        # zero deeper mineral N is a chosen reference profile, not missing data.
        fraction=max(0.,min(hi,25.)-lo)/25.
        no3.append(30.*fraction);nh4.append(5.*fraction)
    profile['SoilLayers']=layers;profile['SubSoilType']=deepcopy(layers[-1])
    data['SoilProfileDescription']=profile
    reg=runpy.run_path(str(ROOT/'06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
    reg['install']();n=reg['load_module']('nitrogen_engine')
    # Same initial available-water convention as existing WLP, full-profile PAW.
    wav=sum((n.theta(l,profile['PFFieldCapacity'])-n.theta(l,profile['PFWiltingPoint']))*l['Thickness'] for l in layers)
    data['site'].update(NO3I=no3,NH4I=nh4,WAV=wav,SMLIM=n.theta(layers[0],profile['PFFieldCapacity']),CO2=400.)
    data['fertilizer_events']=[]
    data.pop('fertilizer_events_by_crop',None)
    data['parameter_provenance'].update(
        soil_water=dict(source='04_Soil_and_Python/Soil_Inputs/Soil_Profile_Demo.json',
            status='BK50 nearby demonstration candidate, not confirmed field'),
        SOC_pH=dict(source='Source_Records/SoilGrids_Aachen_C_N_pH.json',coordinates=[6.088,50.801],
            status='250m gridded estimates, not measurements',conversion='FSOMI = SOC(g/kg)/1000/0.58, consistent with SNOMIN OM-to-C conversion'),
        CNRatioSOMI=dict(source='Published_Reference.json',
            method='17 in 0–25cm, 25 below; published-soil biochemical assumptions transferred to BK50 layers, including deeper profile',
            status='reference assumption, not measured Aachen C:N'),
        total_soil_N=dict(source='SoilGrids nitrogen archived but not used as mineral N',
            reason='Total N is not NO3/NH4; independently predicted SOC/total-N gives low deep-soil C:N and is not adopted as organic C:N'),
        initial_mineral_N=dict(source='Published_Reference.json',
            kg_NO3_N_ha=30.,kg_NH4_N_ha=5.,placement='uniform mass per depth in 0–25cm; zero deeper as an explicit reference assumption',
            status='chosen common starting condition, not a dated field measurement'),
        initial_water=dict(source='Existing Crop_Engine initial_available_water_fraction=1 convention',
            WAV_cm=wav,status='initial-condition assumption; not replenished to full every day'),
        fertilizer_events=dict(value=[],meaning='No fixed scheduled fertiliser; adaptive controller supplies N and records actual applied doses',
            status='management experiment, not unfertilised treatment'),
        fixed_kinetics=dict(source='Existing official SNOMIN reference inputs',status='uncalibrated'))
    data['missing_parameters']=[]
    TARGET.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    issues=n.preflight(data,n.NitrogenConfig(accept_reference_scenario=True,accept_demo_assumptions=True))
    if issues:raise ValueError(issues)
    return TARGET

if __name__=='__main__':print(build())
