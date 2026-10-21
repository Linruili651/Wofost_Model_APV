"""Export unshaded weather from the exact Tianze sky inputs; no PV ray tracing."""
from pathlib import Path
from dataclasses import replace
import hashlib,json,os,tempfile
import numpy as np
import pandas as pd
from run_radiation import load_model,ENGINE,HERE
from project_paths import RESULTS, WEATHER

def main():
    dest=RESULTS/'01_Tables/Open_Field_Radiation'
    notes=dest.parents[1]/'03_Notes/Open_Field_Source'
    dest.mkdir(parents=True,exist_ok=True)
    epw=WEATHER
    raw=pd.read_csv(epw,skiprows=8,header=None)
    online=json.loads((notes/'PVGIS_5_3_TMY_online_check.json').read_text(encoding='utf-8'))
    hours=pd.DataFrame(online['outputs']['tmy_hourly'])
    checks={}
    for col,key in ((13,'G(h)'),(14,'Gb(n)'),(15,'Gd(h)')):
        a=raw[col].to_numpy(float);b=hours[key].to_numpy(float)
        checks[key]=dict(max_abs_difference=float(np.max(np.abs(a-b))),match=bool(np.allclose(a,b,rtol=0,atol=.011)))
    if not all(v['match'] for v in checks.values()):raise ValueError('Online TMY does not match original radiation')
    ns,source=load_model('fixed_tilt')
    scenario=replace(ns['scenario'],start_date='2001-10-15',end_date='2002-10-31',weather_filename=epw.name)
    old=Path.cwd()
    try:
        with tempfile.TemporaryDirectory(prefix='aachen_open_field_') as tmp:
            demo=ns['br'].RadianceObj(name='unshaded_weather_only',path=tmp,hpc=True)
            starts,sampling,_,timing=ns['read_hourly_cultivation_weather'](demo,scenario)
            weather=ns['captured_weather'].copy()
            os.chdir(old)
    finally:os.chdir(old)
    assert len(weather)==382*24
    hourly=pd.DataFrame(dict(hour_start=[t.isoformat() for t in starts],
        hour_end=[t.isoformat() for t in weather.index],solar_timestamp=[t.isoformat() for t in sampling],
        GHI_W_m2=weather.GHI.to_numpy(),DNI_W_m2=weather.DNI.to_numpy(),DHI_W_m2=weather.DHI.to_numpy(),
        duration_h=1.0))
    hourly.to_csv(dest/'Open_Field_Hourly_Matched.csv',index=False,encoding='utf-8-sig')
    hourly['day']=[str(t.date()) for t in starts]
    daily=hourly.groupby('day',sort=True).agg(hour_count=('duration_h','count'),
        GHI_Wh_m2_day=('GHI_W_m2','sum'),DHI_Wh_m2_day=('DHI_W_m2','sum'))
    assert daily.hour_count.eq(24).all() and len(daily)==382
    daily['IRRAD_J_m2_day']=daily.GHI_Wh_m2_day*3600
    daily.to_csv(dest/'Open_Field_Daily_Matched.csv',encoding='utf-8-sig')
    time_column=next(c for c in hours.columns if c.lower().startswith('time'))
    source_hourly=hours[[time_column,'G(h)','Gb(n)','Gd(h)']].copy()
    source_hourly.to_csv(dest/'PVGIS_Original_TMY_Hourly.csv',index=False,encoding='utf-8-sig')
    # Independently check against already finished PV days before using these as a baseline.
    checked=0
    for marker in (HERE/'radiation/fixed_tilt').glob('*/complete.json'):
        date=marker.parent.name
        existing=pd.read_csv(marker.parent/'hourly_weather.csv')
        selected=hourly[hourly.day==date]
        assert len(selected)==len(existing)==24
        np.testing.assert_allclose(selected[['GHI_W_m2','DNI_W_m2','DHI_W_m2']],existing[['GHI','DNI','DHI']],rtol=0,atol=1e-9)
        checked+=1
    report=dict(status='passed',epw_path=str(epw),epw_sha256=hashlib.sha256(epw.read_bytes()).hexdigest(),
        online_source='https://re.jrc.ec.europa.eu/api/v5_3/tmy?lat=50.801&lon=6.088&startyear=2005&endyear=2023&outputformat=json',
        original_online_component_checks=checks,location=online['inputs']['location'],months_selected=online['outputs']['months_selected'],
        model_start='2001-10-15',model_end='2002-10-31',model_years_are_synthetic=True,
        matched_hours=len(hourly),matched_days=len(daily),completed_PV_days_cross_checked=checked,timing=timing,
        definition='No PV shading; natural terrain horizon may be included by PVGIS. GHI recomputed using Tianze solar geometry, DNI and DHI.',
        radiation_method_changed=False)
    (notes/'OPEN_FIELD_VERIFICATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status='passed',online_checks=checks,matched_hours=len(hourly),matched_days=len(daily),
                         completed_PV_days_cross_checked=checked,output=str(dest)),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
