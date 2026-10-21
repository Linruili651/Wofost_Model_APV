"""Run sourced WOFOST81 soil-water/nitrogen cases / WOFOST81. """
from pathlib import Path
import argparse,json,runpy,sys,traceback
_ROOT=next(p for p in Path(__file__).resolve().parents if (p/'06_Hao_Interface_and_Rerun').is_dir())
_registry=runpy.run_path(str(_ROOT/'06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
_registry['install']()
n=_registry['load_module']('nitrogen_engine')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crop',choices=list(n.base.crop_catalog())+['all'],default='all')
    parser.add_argument('--mode',choices=list(n.MODELS)+['all'],default='NWLP_MLWB_SNOMIN')
    parser.add_argument('--nitrogen-inputs',default=n.DEFAULT_FIELD)
    parser.add_argument('--accept-reference-scenario',action='store_true')
    parser.add_argument('--accept-demo-assumptions',action='store_true')
    parser.add_argument('--harvest-year',type=int,default=2002)
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args();rows=[]
    for mode in (list(n.MODELS) if args.mode=='all' else [args.mode]):
        for crop in (list(n.base.crop_catalog()) if args.crop=='all' else [args.crop]):
            config=n.NitrogenConfig(crop_id=crop,mode=mode,harvest_year=args.harvest_year,
                nitrogen_inputs=args.nitrogen_inputs,accept_reference_scenario=args.accept_reference_scenario,
                accept_demo_assumptions=args.accept_demo_assumptions)
            data=n.load_inputs(config);issues=n.preflight(data,config)
            row=dict(crop_id=crop,crop_label=config.spec()['label'],mode=mode,
                nitrogen_input_scenario=data['scenario_id'],scenario_kind=data['scenario_kind'])
            if issues:row.update(status='blocked_missing_sourced_inputs',missing_parameters=issues,nitrogen_leaching_kg_N_ha=None)
            elif args.check_only:row.update(status='inputs_complete_not_executed')
            else:
                try:
                    payload,folder=n.evaluate(config)
                    row.update({k:payload.get(k) for k in ['status','model','yield_kg_DM_ha','storage_organ_DM_kg_ha','all_points_mature',
                        'nitrogen_leaching_kg_N_ha','nitrate_leaching_kg_N_ha','ammonium_leaching_kg_N_ha','denitrification_kg_N_ha',
                        'fertilizer_N_applied_kg_N_ha','biological_N_fixation_kg_N_ha','drainage_bottom_mm',
                        'water_balance_max_abs_residual_mm','nitrogen_balance_max_abs_residual_kg_N_ha','eligible_for_field_optimization']})
                    row['output_directory']=folder.relative_to(n.ROOT).as_posix()
                except Exception as exc:
                    row.update(status='execution_failed',error=repr(exc),traceback=traceback.format_exc(),nitrogen_leaching_kg_N_ha=None)
            rows.append(row);print(crop,mode,row['status'],row.get('nitrogen_leaching_kg_N_ha'),flush=True)
    out=n.ROOT/'06_Hao_Interface_and_Rerun/Rerun_Results/Nitrogen_Verification'
    out.mkdir(parents=True,exist_ok=True)
    label='Field_Readiness-Aachen' if data['scenario_kind']=='field' else 'Reference_Runs-'
    n.base.save_json(out/(label+'.json'),rows)
    n.pd.DataFrame([{k:v for k,v in row.items() if k not in ['traceback','missing_parameters']} for row in rows]).to_csv(out/(label+'.csv'),index=False,encoding='utf-8-sig')
    print(out,flush=True)
    if any(row['status']=='execution_failed' for row in rows):raise SystemExit(1)
    if any(row['status']=='blocked_missing_sourced_inputs' for row in rows):raise SystemExit(2)

if __name__=='__main__':main()
