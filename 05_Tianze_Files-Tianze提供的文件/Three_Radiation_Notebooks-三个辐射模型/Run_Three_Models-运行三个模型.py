"""Execute preserved Tianze notebook code with explicitly recorded smoke inputs."""
from pathlib import Path
import argparse, contextlib, hashlib, io, json, os, sys, time, traceback, tempfile, uuid

sys.stdout.reconfigure(encoding='utf-8')
root=Path(__file__).resolve().parent
package_root=root.parents[1]
weather=package_root/'03_Precipitation-降水条件/Aachen_TMY_Weather-Aachen典型年天气.epw'
parser=argparse.ArgumentParser(description="Run short Tianze radiation checks / 天泽辐射模型短时检查")
parser.add_argument('--model',choices=['fixed_tilt','vertical_pv','single_axis','all'],default='all')
parser.add_argument('--radiance-home',type=Path,help='Radiance root containing bin and lib / 含bin和lib的Radiance根目录')
args=parser.parse_args()
if args.radiance_home:
    rad=args.radiance_home.resolve()
    os.environ['PATH']=str(rad/'bin')+os.pathsep+os.environ['PATH']
    os.environ['RAYPATH']=os.pathsep.join([str(rad/'lib'),'.'])
import shutil
for executable in ['rtrace','oconv','genbox','xform','gendaylit']:
    if not shutil.which(executable):
        raise RuntimeError(f'Missing Radiance tool / 缺少Radiance外部程序: {executable}')
stamp=time.strftime('%Y%m%d_%H%M%S')
models=[('fixed_tilt','固定倾角'),('vertical_pv','垂直光伏'),('single_axis','单轴跟踪')]
failures=0
for stem,label in models:
    if args.model not in ('all',stem):continue
    run=root/'Rerun_Results-复跑结果'/f'{stem}_{stamp}-{label}'
    run.mkdir(parents=True,exist_ok=True)
    src=root/'Original_Notebooks-原始笔记本'/f'{stem}-{label}.ipynb'
    nb=json.loads(src.read_text(encoding='utf-8'))
    nb['metadata']['kernelspec']={'name':'python3','display_name':'Python 3','language':'python'}
    for c in nb['cells']:
        if c['cell_type']=='code':c.update(outputs=[],execution_count=None)
    overrides=f'''# Smoke Inputs-短时运行参数; original optical/geometry algorithms unchanged.
from dataclasses import replace
SETTINGS = replace(SETTINGS, n_workers=2)
scenario = replace(scenario, scenario_name="Aachen_{stem}_smoke_20261019",
    start_date="2024-06-21 12:00", end_date="2024-06-21 13:00",
    weather_filename={weather.name!r}, ground_grid_x=4, ground_grid_y=4)
array_specification = replace(array_specification, n_mods=2, n_rows=2)
GET_LINRUI_GROUND_IRRADIATION = True
GET_HAO_ARRAY_RESULTS = True
WEATHER_DIRECTORY = Path({str(weather.parent)!r})
RESULTS_DIRECTORY = Path({str(run)!r})
HAO_RESULTS_FILE = RESULTS_DIRECTORY / "Hao_Hourly_Radiation-Hao逐小时辐射.csv"
LINRUI_RESULTS_FILE = RESULTS_DIRECTORY / "Linrui_Period_Ground_Radiation-Linrui时段地面辐射.csv"
print("Smoke run: 1 daylight hour, 2x2 modules, 4x4 ground grid; both outputs enabled.")
'''
    nb['cells'].insert(9,{'cell_type':'code','metadata':{},'source':overrides.splitlines(keepends=True),'outputs':[],'execution_count':None})
    nb['cells'].insert(0,{'cell_type':'markdown','metadata':{},'source':['# Smoke Run-短时运行副本\n','One daylight hour, 2×2 modules, 4×4 ground sensors; both outputs on. Original source kept separately. / 一小时日照、2×2组件、4×4地面网格，打开两类输出，原文件另存。\n']})
    for index,cell in enumerate(nb['cells']):
        cell.setdefault('id',uuid.uuid5(uuid.NAMESPACE_URL,stem+':'+str(index)).hex[:10])
    ns={'__name__':'__main__','display':lambda obj:print(obj.to_string() if hasattr(obj,'to_string') else obj)}
    logs=[];start=time.time();status='passed';error=None;count=0
    print('START',stem,flush=True)
    old=Path.cwd();os.chdir(run)
    try:
        for idx,c in enumerate(nb['cells']):
            if c['cell_type']!='code':continue
            count+=1;buf=io.StringIO();c['execution_count']=count
            try:
                with contextlib.redirect_stdout(buf),contextlib.redirect_stderr(buf):
                    exec(compile(''.join(c['source']),f'{src.name}:cell{idx}','exec'),ns)
            except Exception as exc:
                status='failed';error=f'{type(exc).__name__}: {exc}'
                trace=traceback.format_exc();buf.write(trace)
                c['outputs'].append({'output_type':'error','ename':type(exc).__name__,'evalue':str(exc),'traceback':trace.splitlines()})
            txt=buf.getvalue();logs.append(f'CELL {idx}\n{txt}')
            if txt:c['outputs'].insert(0,{'output_type':'stream','name':'stdout','text':txt.splitlines(keepends=True)})
            print(stem,'cell',idx,status,round(time.time()-start,1),'s',flush=True)
            if status=='failed':print(txt[-3500:],flush=True);break
    finally:os.chdir(old)
    summary={'model':stem,'status':status,'error':error,'elapsed_seconds':round(time.time()-start,2),
        'original_path':src.relative_to(root).as_posix(),'original_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
        'weather_sha256':hashlib.sha256(weather.read_bytes()).hexdigest(),
        'start_date':'2024-06-21 12:00','end_date_exclusive':'2024-06-21 13:00',
        'array':[2,2],'ground_grid':[4,4],'accuracy':'low','workers':2,
        'calculate_hao':True,'calculate_linrui':True,'source_algorithm_modified':False}
    if status=='passed':
        hao=ns['hao_hourly'];ground=ns['ground_summary']
        summary.update(hourly_rows=len(hao),hourly_energy={k:float(hao[k].sum()) for k in hao.columns if 'energy_Wh' in k},ground=ground)
    (run/'Execution_Record-执行记录.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (run/'Execution_Log-执行日志.txt').write_text('\n\n'.join(logs),encoding='utf-8')
    (run/f'{stem}_Smoke_Executed-{label}短时执行.ipynb').write_text(json.dumps(nb,ensure_ascii=False,indent=1),encoding='utf-8')
    print('DONE',stem,status,flush=True)
    failures += status != 'passed'
if failures:
    raise SystemExit(1)
