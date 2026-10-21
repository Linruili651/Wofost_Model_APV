from pathlib import Path
import os,sys,runpy,json,shutil,hashlib,ast
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[1]
registry=runpy.run_path(str(ROOT/'06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
base=registry['install']();n=registry['load_module']('nitrogen_engine')
def new_run(label):
    path=AUDIT/'reference81'/label;path.mkdir(parents=True,exist_ok=False);return path
n.base.new_run=new_run
rows=[]
for mode in n.MODELS:
    for crop in base.crop_catalog():
        cfg=n.NitrogenConfig(crop_id=crop,mode=mode,nitrogen_inputs=n.REFERENCE,accept_reference_scenario=True,accept_demo_assumptions=True)
        payload,folder=n.evaluate(cfg)
        rows.append({k:payload.get(k) for k in ('crop_id','mode','model','model_version','status','yield_kg_DM_ha',
            'transpiration_mm','soil_evaporation_mm','nitrogen_leaching_kg_N_ha','water_balance_max_abs_residual_mm',
            'nitrogen_balance_max_abs_residual_kg_N_ha','leaching_boundary_depth_cm')})
        print(crop,mode,payload['status'],flush=True)
base.save_json(AUDIT/'reference81_summary.json',rows)
import pandas as pd
pd.DataFrame(rows).to_csv(AUDIT/'reference81_summary.csv',index=False)
# Gather test-created run directories into this audit folder.
old=ROOT/'06_Hao_Interface_and_Rerun/Rerun_Results'
cutoff=(AUDIT/'rerun.py').stat().st_ctime
moved=[]
for path in list(old.rglob('Run_*')):
    if path.is_dir() and path.stat().st_ctime>=cutoff:
        target=AUDIT/'test_outputs'/path.relative_to(old);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(path),str(target));moved.append(dict(original=str(path),current=str(target)))
base.save_json(AUDIT/'test_output_locations.json',moved)
for name in ('Fertilizer_Check.json',):
    source=ROOT/'06_Hao_Interface_and_Rerun/Validation'/name
    shutil.copy2(source,AUDIT/name)
# Syntax check project-owned active code; no Radiance execution.
checked=[]
for directory in ('01_PP_Model','02_WLP_Model','03_Precipitation',
                  '06_Hao_Interface_and_Rerun/Shared_Core','07_Full_Season_Run'):
    for path in (ROOT/directory).rglob('*.py'):
        if any(x in path.parts for x in ('Runtime_Cache-','__pycache__')):continue
        ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path));checked.append(str(path.relative_to(ROOT)))
base.save_json(AUDIT/'syntax_checks.json',dict(status='passed',count=len(checked),files=checked,radiance_executed=False))
files=[ROOT/'README_Start_Here.md',ROOT.parent/'Thesis_Linrui.docx']
files+=list((ROOT/'06_Hao_Interface_and_Rerun/Shared_Core').glob('*.py'))
files+=list((ROOT/'02_WLP_Model/Nitrogen_Extension').glob('*.py'))
files+=list((ROOT/'07_Full_Season_Run').glob('*.py'))
snapshot=[]
for path in files:
    relative=path.relative_to(ROOT) if path.is_relative_to(ROOT) else Path(path.name)
    target=AUDIT/'source_snapshot'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    snapshot.append(dict(source=str(path),snapshot=str(target.relative_to(AUDIT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
base.save_json(AUDIT/'source_manifest.json',snapshot)
print('TECHNICAL_CHECKS_COMPLETE',len(rows),len(checked),flush=True)
