"""Check or run the preserved Tianze Aachen radiation models with local tools."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

from runtime_env import HERE,check,configure


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--action',choices=['check','smoke'],default='check')
    parser.add_argument('--model',choices=['fixed_tilt','vertical_pv','single_axis','all'],default='fixed_tilt')
    args=parser.parse_args()
    report=check()
    if args.action=='check':return
    part=HERE.parent
    model_dir=part/'Three_Radiation_Notebooks-三个辐射模型'
    runner=model_dir/'Run_Three_Models-运行三个模型.py'
    before=set((model_dir/'Rerun_Results-复跑结果').glob('*/Execution_Record-执行记录.json'))
    home,_=configure()
    process=subprocess.run([sys.executable,str(runner),'--radiance-home',str(home),'--model',args.model],cwd=model_dir)
    after=set((model_dir/'Rerun_Results-复跑结果').glob('*/Execution_Record-执行记录.json'))
    records=[]
    for path in sorted(after-before):
        record=json.loads(path.read_text(encoding='utf-8-sig'))
        records.append(dict(record_file=str(path),**record))
    passed=process.returncode==0 and bool(records) and all(r.get('status')=='passed' for r in records)
    result=dict(date='2026-10-19',scope='Aachen one-hour software smoke run; no full-season crop comparison',
        success=passed,returncode=process.returncode,installation_check=report,
        source_notebooks_modified=False,records=records)
    (HERE/'AACHEN_SMOKE_CHECK-亚琛短时验证.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if not passed:raise SystemExit(process.returncode or 1)
    print('Aachen Radiance smoke run passed. Full record: '+str(HERE/'AACHEN_SMOKE_CHECK-亚琛短时验证.json'))


if __name__=='__main__':main()
