"""Matched six-crop WOFOST73 PP / WLP_MLWB interface for Hao."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import json
import math

import numpy as np
import pandas as pd
import yaml

from legacy_bridge import (ROOT, CropConfig as WeatherConfig, GroundGrid, read_epw_daily,
                           _weather_provider, load_pcse, sha256, fingerprint, save_json, new_run,
                           validate_radiation)
from precipitation_adapter import attach_precipitation


def crop_catalog():
    return json.loads((ROOT / "06_Hao_Interface_and_Rerun/Shared_Inputs/Crop_Catalog.json").read_text(encoding="utf-8"))["crops"]


@dataclass(frozen=True)
class ModelConfig:
    crop_id: str = "winter_wheat"
    mode: str = "PP"
    harvest_year: int = 2002  # synthetic TMY labels, not observed historical weather
    accept_demo_assumptions: bool = False
    soil_profile: str = "04_Soil_and_Python/Soil_Inputs/Soil_Profile_Demo.json"
    co2_ppm: float = 360.0  # reference concentration, explicitly not current atmosphere
    initial_available_water_fraction: float = 1.0
    epw_wind_height_m: float = 10.0
    angstrom_a: float = 0.29
    angstrom_b: float = 0.49

    def spec(self):
        if self.crop_id not in crop_catalog():
            raise ValueError(f"Unknown crop_id: {self.crop_id}")
        if self.mode not in ("PP", "WLP_MLWB"):
            raise ValueError("mode must be PP or WLP_MLWB; nitrogen is a separate future extension")
        if not 320 <= self.co2_ppm <= 700 or not 0 <= self.initial_available_water_fraction <= 1:
            raise ValueError("CO2 or initial water fraction out of range")
        return deepcopy(crop_catalog()[self.crop_id])

    def weather_config(self):
        s = self.spec()
        return WeatherConfig(variety=s["variety"],
            start=f"{self.harvest_year - int(s['cross_year'])}-{s['start_mm_dd']}",
            end=f"{self.harvest_year}-{s['end_mm_dd']}", start_type="sowing",
            accept_demo_assumptions=self.accept_demo_assumptions,
            allow_missing_rain_for_pp=False, epw_wind_height_m=self.epw_wind_height_m,
            angstrom_a=self.angstrom_a, angstrom_b=self.angstrom_b)


def prepare_weather(config):
    wc = config.weather_config()
    epw = ROOT / "03_Precipitation/Aachen_TMY_Weather.epw"
    frame, info = read_epw_daily(epw, wc)
    frame, rain = attach_precipitation(frame, epw,
        ROOT / "03_Precipitation/Precipitation_Supplement.json", component="liquid_rain")
    info.update(rain)
    info.update(model_dates_are_synthetic=True, snowmelt_included=False,
                uniform_open_field_rain_until_explicit_spatial_input=True)
    return frame, info


def load_parameters(config):
    spec = config.spec()
    path = ROOT / '06_Hao_Interface_and_Rerun/Shared_Inputs/Crop_Parameters' / {'wheat': 'Wheat.yaml', 'barley': 'Barley.yaml', 'maize': 'Maize.yaml', 'potato': 'Potato.yaml', 'sugarbeet': 'Sugar_Beet.yaml', 'soybean': 'Soybean.yaml'}[spec["crop_name"]]
    source = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw = source["CropParameters"]["Varieties"][spec["variety"]]
    crop = {k: deepcopy(v[0]) for k, v in raw.items() if k != "Metadata"}
    soil_path = Path(config.soil_profile)
    if not soil_path.is_absolute():
        soil_path = ROOT / soil_path
    soil_source = json.loads(soil_path.read_text(encoding="utf-8"))
    if not config.accept_demo_assumptions:
        raise ValueError("Read README.md and explicitly enable the uncalibrated demonstration assumptions.")
    profile = deepcopy(soil_source["SoilProfileDescription"])
    if profile.get("GroundWater"):
        raise ValueError("PCSE's bundled layered water balance does not implement groundwater influence.")
    raw_rdmcr = float(crop["RDMCR"])
    soil_root_limit = float(soil_source["demonstration_soil_root_limit_cm"])
    root_limit = min(raw_rdmcr, soil_root_limit, sum(l["Thickness"] for l in profile["SoilLayers"]))
    if root_limit < float(crop["RDI"]):
        raise ValueError("Rootable soil depth is less than initial crop rooting depth")
    # MLWB validates RDMCR against a layer boundary. Preserve total profile depth;
    # split layers at root limit and at <=20cm intervals without changing properties.
    crop["RDMCR"] = root_limit
    crop["IAIRDU"] = int(crop.get("IAIRDU", 0))
    refined, top = [], 0.0
    for layer in profile["SoilLayers"]:
        bottom = top + float(layer["Thickness"])
        fixed = sorted(set([top, bottom] + ([10.] if top < 10 < bottom else [])
                     + ([root_limit] if top < root_limit < bottom else [])))
        boundaries=[top]
        for a,b in zip(fixed,fixed[1:]):
            if b-a < 5-1e-8:
                raise ValueError("A required soil/root boundary creates a layer thinner than PCSE's 5cm minimum")
            n=math.ceil((b-a)/20)
            boundaries.extend(a+(b-a)*i/n for i in range(1,n+1))
        for a, b in zip(boundaries, boundaries[1:]):
            child = deepcopy(layer)
            child.update(Thickness=b-a, SoilID=f"{layer['SoilID']}__{a:g}_{b:g}cm")
            refined.append(child)
        top = bottom
    profile["SoilLayers"] = refined
    first = refined[0]
    def theta(layer, pf):
        a=np.array(layer["SMfromPF"]).reshape(-1,2)
        return float(np.interp(pf, a[:,0], a[:,1]))
    fc = theta(first, profile["PFFieldCapacity"])
    wp = theta(first, profile["PFWiltingPoint"])
    sat = theta(first, -1)
    soil = dict(SMW=wp, SMFCF=fc, SM0=sat, CRAIRC=first["CRAIRC"],
                RDMSOL=root_limit, SoilProfileDescription=profile)
    # WAV is available water above wilting point. PCSE distributes it internally;
    # a fraction=1 does not assert that every layer starts exactly at field capacity.
    wav = config.initial_available_water_fraction * sum(
        (theta(l, profile["PFFieldCapacity"])-theta(l,profile["PFWiltingPoint"]))*l["Thickness"]
        for l in refined)
    load_pcse()
    from pcse.input import WOFOST73SiteDataProvider
    site = dict(WOFOST73SiteDataProvider(WAV=wav, CO2=config.co2_ppm, SMLIM=fc,
                NOTINF=0., IFUNRN=0, SSI=0., SSMAX=0.))
    info=dict(crop_name=spec["crop_name"], variety=spec["variety"], metadata=raw["Metadata"],
              yaml_sha256=sha256(path), soil_sha256=sha256(soil_path),
              source_RDMCR_cm=raw_rdmcr, applied_RDMCR_cm=root_limit,
              root_limit_source="Demo assumption: min(crop RDMCR, BK50 reference effective root depth)",
              soil_status=soil_source["status"], soil_unit=soil_source["source"]["selected_map_feature"]["Name"],
              soil_assumptions=soil_source["assumptions"], crop_parameters=crop)
    return crop, soil, site, info


def run_point(frame, config, *, radiation=None, effective_rain=None):
    spec, wc = config.spec(), config.weather_config()
    if list(frame.day) != wc.dates():
        raise ValueError("Weather must cover the configured season once, in exact daily order")
    if frame.RAIN_mm_day.isna().any():
        raise ValueError("Complete precipitation is required for both paired entry points")
    actual_frame = frame.copy(deep=True)
    if effective_rain is not None:
        values=np.asarray(effective_rain,float)
        if values.shape != (len(frame),) or not np.isfinite(values).all() or (values<0).any():
            raise ValueError("effective_rain_mm_day must be complete, finite and non-negative")
        actual_frame["RAIN_mm_day"]=values
    crop, soil, site, parameter_info = load_parameters(config)
    from pcse.base import ParameterProvider
    from pcse.models import Wofost73_PP, Wofost73_WLP_MLWB
    params=ParameterProvider(cropdata=crop, soildata=deepcopy(soil), sitedata=site)
    first,last=wc.dates()[0],wc.dates()[-1]
    management=[{first: {"CropCalendar":dict(crop_name=spec["crop_name"],variety_name=spec["variety"],
        crop_start_date=first,crop_start_type="sowing",crop_end_date=last,
        crop_end_type="earliest",max_duration=(last-first).days+1),"TimedEvents":None,"StateEvents":None}}]
    provider=_weather_provider(actual_frame,wc,actual_frame.IRRAD if radiation is None else radiation)
    provider.description=["Aachen synthetic TMY; matched WOFOST73 PP or layered WLP; liquid rain only"]
    cls=Wofost73_PP if config.mode=="PP" else Wofost73_WLP_MLWB
    common=["DVS","LAI","TAGP","TWSO","TWRT","RD","SM","TRA","EVS","RFTRA"]
    terminal=["EVST","WTRAT"]
    if config.mode=="WLP_MLWB":
        common += ["WC","Flow","BOTTOMFLOW","BOTTOMFLOWT","TSR","SS"]
        terminal += ["WC","SS","RAINT","TOTIRR","TOTINF","BOTTOMFLOWT","TSR","EVWT"]
    model=cls(params,provider,management,output_vars=common,terminal_vars=terminal)
    initial = None
    if config.mode=="WLP_MLWB":
        initial=dict(water_cm=float(model.soil.states.WC.sum()),surface_cm=float(model.soil.states.SS))
    model.run_till_terminate()
    raw=model.get_output();summary=model.get_summary_output()[0];term=model.get_terminal_output()
    mature=summary.get("DOM") is not None and float(summary["DVS"])>=1.999
    harvested=summary.get("DOH") is not None
    usable=mature or (spec["organ"] != "grain" and harvested)
    layers=[];daily=[]
    profile=soil["SoilProfileDescription"]["SoilLayers"]
    for row in raw:
        flat={k:v for k,v in row.items() if not isinstance(v,(list,tuple,np.ndarray))}
        if config.mode=="WLP_MLWB":
            top=0.
            for idx,(sm,water,layer) in enumerate(zip(row["SM"],row["WC"],profile)):
                bottom=top+layer["Thickness"]
                flow=row.get("Flow")
                layers.append(dict(day=row["day"],layer=idx+1,top_cm=top,bottom_cm=bottom,
                    SM_m3_m3=float(sm),water_mm=float(water)*10,
                    upper_flow_mm_day=None if flow is None else float(flow[idx])*10,
                    lower_flow_mm_day=None if flow is None else float(flow[idx+1])*10))
                top=bottom
        daily.append(flat)
    residual=None
    if initial is not None:
        residual=10*(initial["surface_cm"]-term["SS"]+initial["water_cm"]-float(np.sum(term["WC"]))
            +term["RAINT"]+term["TOTIRR"]-term["WTRAT"]-term["EVST"]-term["EVWT"]-term["TSR"]-term["BOTTOMFLOWT"])
        if abs(residual)>0.001:
            raise ValueError(f"Water balance residual exceeds 0.001mm: {residual}")
    actual_weather=pd.DataFrame([{k:getattr(provider(d),k) for k in
        ("DAY","IRRAD","RAIN","TMIN","TMAX","TEMP","VAP","WIND","E0","ES0","ET0")}
        for d in [r["day"] for r in raw]])
    return dict(daily=pd.DataFrame(daily),soil_daily=pd.DataFrame(layers),summary=summary,
        terminal=term,actual_weather=actual_weather,mature=mature,harvested=harvested,usable=usable,
        storage_organ_DM_kg_ha=float(summary["TWSO"]),crop_parameters=parameter_info,soil=soil,site=site,
        management=management,model=cls.__name__,water_balance_residual_mm=residual,
        water=dict(transpiration_mm=float(term["WTRAT"])*10,soil_evaporation_mm=float(term["EVST"])*10,
            drainage_bottom_mm=None if config.mode=="PP" else float(term["BOTTOMFLOWT"])*10,
            runoff_mm=None if config.mode=="PP" else float(term["TSR"])*10))


def evaluate(config, *, radiation=None, scenario_id="natural_light", provenance=None,
             grid=None, baseline=None, spatial_mode="pointwise"):
    frame,weather_info=prepare_weather(config)
    grid=grid or GroundGrid()
    points=grid.points();area=float(points.cell_area_m2.sum())
    if spatial_mode not in ("pointwise","area_mean_approximation"):
        raise ValueError("Invalid spatial_mode")
    if scenario_id=="natural_light":
        if radiation is not None:
            raise ValueError("Natural baseline must use EPW GHI without a shading table")
        jobs=[("whole_plot",area,frame.IRRAD.to_numpy(),None)]
    else:
        if radiation is None or not provenance:
            raise ValueError("APV requires full daily point radiation and explicit provenance")
        if isinstance(radiation,(str,Path)): radiation=pd.read_csv(radiation)
        selected=validate_radiation(frame,radiation,scenario_id,grid)
        if "effective_rain_mm_day" in selected:
            rain=selected.effective_rain_mm_day.to_numpy(float)
            if not np.isfinite(rain).all() or (rain<0).any():raise ValueError("Invalid spatial rainfall")
        if spatial_mode=="area_mean_approximation":
            r=(selected.total_Wh_m2_day*selected.cell_area_m2).groupby(selected.day).sum().reindex(frame.day).to_numpy()/area
            p=None
            if "effective_rain_mm_day" in selected:
                p=(selected.effective_rain_mm_day*selected.cell_area_m2).groupby(selected.day).sum().reindex(frame.day).to_numpy()/area
            jobs=[("area_mean",area,r*3600,p)]
        else:
            jobs=[]
            for pid,g in selected.groupby("point_id",sort=True):
                ordered=g.set_index("day").reindex(frame.day)
                rain=ordered.effective_rain_mm_day.to_numpy(float) if "effective_rain_mm_day" in ordered else None
                jobs.append((pid,float(g.cell_area_m2.iloc[0]),ordered.total_Wh_m2_day.to_numpy(float)*3600,rain))
    output=[];daily=[];soil_daily=[];weather=[];last=None
    for pid,weight,irrad,rain in jobs:
        r=run_point(frame,config,radiation=irrad,effective_rain=rain);last=r
        output.append(dict(point_id=pid,cell_area_m2=weight,mature=r["mature"],harvested=r["harvested"],usable=r["usable"],
            storage_organ_DM_kg_ha=r["storage_organ_DM_kg_ha"],DVS=float(r["summary"]["DVS"]),
            end_date=str(r["daily"].day.iloc[-1]),root_depth_cm=float(r["summary"]["RD"]),
            water_balance_residual_mm=r["water_balance_residual_mm"],**r["water"]))
        for target,key in [(daily,"daily"),(soil_daily,"soil_daily"),(weather,"actual_weather")]:
            d=r[key].copy()
            if not d.empty:d.insert(0,"point_id",pid);target.append(d)
    table=pd.DataFrame(output)
    def avg(key):
        if table[key].isna().any():return None
        return float(np.average(table[key],weights=table.cell_area_m2))
    identity=fingerprint(dict(config=asdict(config),weather=frame.to_json(date_format="iso"),grid=asdict(grid),
        crop_yaml=last["crop_parameters"]["yaml_sha256"],soil=last["crop_parameters"]["soil_sha256"],
        engine_sha256=sha256(__file__),catalog_sha256=sha256(ROOT/"06_Hao_Interface_and_Rerun/Shared_Inputs/Crop_Catalog.json"),spatial_mode=spatial_mode))
    usable=bool(table.usable.all());value=avg("storage_organ_DM_kg_ha")
    payload=dict(schema_version="hao-crop-yield-v2",crop_id=config.crop_id,crop_label=config.spec()["label"],
        harvest_organ=config.spec()["organ"],mode=config.mode,model=last["model"],pcse_version="6.0.13",
        scenario_id=scenario_id,field_validated=False,
        status="uncalibrated_harvest_result" if usable else "grain_not_mature_by_cutoff_do_not_optimise",
        all_points_mature=bool(table.mature.all()),all_points_usable=usable,
        storage_organ_DM_kg_ha=value, yield_kg_DM_ha=value if usable else None,
        yield_kg_DM_m2=value/10000 if usable else None,total_storage_organ_DM_kg_on_plot=value*area/10000 if usable else None,
        fresh_or_marketable_yield_t_ha=None,common_planted_area_m2=area,relative_yield_to_natural=None,
        comparison_fingerprint=identity,config=asdict(config),
        transpiration_mm=avg("transpiration_mm"),soil_evaporation_mm=avg("soil_evaporation_mm"),
        drainage_bottom_mm=avg("drainage_bottom_mm"),runoff_mm=avg("runoff_mm"),
        irrigation_applied_mm=0.0,irrigation_requirement_mm=None,nitrogen_leaching_kg_N_ha=None,
        water_balance_max_abs_residual_mm=None if config.mode=="PP" else float(table.water_balance_residual_mm.abs().max()),
        reference_table_row=config.spec(),weather_provenance=weather_info,radiation_provenance=provenance,
        rainfall_spatial_assumption="explicit effective_rain_mm_day" if any(j[3] is not None for j in jobs) else "uniform open-field liquid rain; panel redistribution absent",
        limitations=["Synthetic TMY and liquid rain only; no snowmelt or ice.",
            "BK50 candidate soil and hydraulic curve fit are uncalibrated demonstration assumptions.",
            "PP has no dynamic soil-water balance; WLP_MLWB has no nitrogen cycling.",
            "All yields are storage-organ dry matter, not market fresh yield or economic profit.",
            "Near-ground daily radiation and open-field reference ET are approximate APV coupling.",
            "Independent soil columns have no lateral water or nitrogen exchange."])
    if config.spec()["organ"]=="grain":
        payload["total_grain_DM_kg_on_plot"]=payload["total_storage_organ_DM_kg_on_plot"]
    if baseline is not None:
        if baseline.get("scenario_id")!="natural_light" or baseline.get("comparison_fingerprint")!=identity:
            raise ValueError("Baseline must match crop, mode, soil, calendar, weather and grid")
        base=baseline.get("yield_kg_DM_ha")
        if usable and base is not None and base>0:payload["relative_yield_to_natural"]=value/base
    folder=new_run(f"{config.mode}/{config.crop_id}")
    payload["run_id"]=folder.name
    table.to_csv(folder/"Point_Summary.csv",index=False,encoding="utf-8-sig")
    pd.concat(daily,ignore_index=True).to_csv(folder/"Daily_Crop_Growth.csv",index=False,encoding="utf-8-sig")
    pd.concat(weather,ignore_index=True).to_csv(folder/"Actual_Model_Weather.csv",index=False,encoding="utf-8-sig")
    if soil_daily:pd.concat(soil_daily,ignore_index=True).to_csv(folder/"Daily_Soil_Layers.csv",index=False,encoding="utf-8-sig")
    if scenario_id!="natural_light":selected.to_csv(folder/"Daily_Point_Radiation.csv",index=False,encoding="utf-8-sig")
    save_json(folder/"Hao_Crop_Yield.json",payload)
    save_json(folder/"Configuration_and_Parameters.json",dict(config=asdict(config),parameters=last["crop_parameters"],
        soil=last["soil"],site=last["site"],management=last["management"]))
    save_json(folder/"Units.json",dict(yield_kg_DM_ha="kg storage-organ dry matter/ha",RAIN="cm/day",IRRAD="J/m2/day",
        SM_m3_m3="m3 water/m3 soil",water_mm="mm water",RD="cm",nitrogen_leaching_kg_N_ha="not implemented; null"))
    return payload,folder
