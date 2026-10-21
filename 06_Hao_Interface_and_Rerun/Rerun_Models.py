"""Run PP, layered WLP or both for the six crops in Hao's reference table."""

# Load bilingual file paths through stable internal Python module names.
from pathlib import Path as _Path
import runpy as _runpy
_package_root = next(p for p in _Path(__file__).resolve().parents if (p / '06_Hao_Interface_and_Rerun').is_dir())
_registry = _runpy.run_path(str(_package_root / '06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
_registry["install"]()
from pathlib import Path
import argparse
import json
import pandas as pd
from crop_engine import ROOT, ModelConfig, crop_catalog, evaluate, save_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["PP","WLP_MLWB","both"],default="both")
    parser.add_argument("--crop", choices=list(crop_catalog())+["all"],default="all")
    parser.add_argument("--accept-demo-assumptions",action="store_true")
    parser.add_argument("--harvest-year",type=int,default=2002)
    parser.add_argument("--soil-profile",default="04_Soil_and_Python/Soil_Inputs/Soil_Profile_Demo.json")
    args=parser.parse_args()
    rows=[]
    for mode in (["PP","WLP_MLWB"] if args.mode=="both" else [args.mode]):
        for crop_id in (list(crop_catalog()) if args.crop=="all" else [args.crop]):
            config=ModelConfig(crop_id=crop_id,mode=mode,harvest_year=args.harvest_year,
                soil_profile=args.soil_profile,accept_demo_assumptions=args.accept_demo_assumptions)
            payload,folder=evaluate(config)
            rows.append({k:payload[k] for k in ["crop_id","crop_label","mode","model","status",
                "yield_kg_DM_ha","storage_organ_DM_kg_ha","all_points_mature",
                "transpiration_mm","soil_evaporation_mm","drainage_bottom_mm","runoff_mm",
                "water_balance_max_abs_residual_mm"]}|{"output_directory":folder.relative_to(ROOT).as_posix()})
            print(crop_id,mode,payload["status"],payload["yield_kg_DM_ha"],flush=True)
    out=ROOT/"06_Hao_Interface_and_Rerun/Rerun_Results/Reference_Comparison"
    out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out/"Six_Crop_PP_WLP_Comparison.csv",index=False,encoding="utf-8-sig")
    save_json(out/"Six_Crop_PP_WLP_Comparison.json",rows)
    print(out,flush=True)


if __name__=="__main__":main()
