"""Read-only local progress page. Does not launch or change model calculations."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
import ctypes, json, time, os, sys

HERE=Path(__file__).resolve().parent
from project_paths import RESULTS
PAGE=RESULTS/'View_Progress.html'

def read(path):
    try:return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError,ValueError):return {}

def alive(pid):
    if not pid:return False
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
    kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x1000,False,int(pid))
    if not handle:return False
    code=ctypes.c_ulong()
    try:return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
    finally:kernel.CloseHandle(handle)

def render():
    status=read(HERE/'status.json');process=read(HERE/'pipeline_process.json')
    export=read(RESULTS/'EXPORT_STATUS.json')
    running=alive(process.get('pid'))
    complete=export.get('status')=='complete'
    failed=process.get('status')=='failed'
    state='Completed' if complete else 'Error' if failed else 'Calculating' if running else 'Calculation process is not running; check the logs.'
    phase=status.get('phase','Waiting for progress data')
    done=int(status.get('completed_days',0));total=int(status.get('total_days',382))
    summaries=len(list((HERE/'crop_results').glob('*/*/*/summary.json')))
    if phase=='crops':
        title='Crop simulation progress';count=f'{summaries} / 36  treatments completed';percent=min(100,summaries/36*100)
        detail=f"Current crop: {status.get('crop','')}; Mode: {status.get('mode','')}; Treatment: {status.get('case','')}; Sampling point: {status.get('completed_points',0)} / {status.get('total_points',0)}"
    elif complete:
        title='Result export progress';count=f"36 Treatment, {export.get('figures',12)}  figures completed";percent=100;detail='Final results have been exported to this folder.'
    else:
        title='Radiation progress';count=f'{done} / {total}  days completed';percent=min(100,100*done/max(total,1))
        detail=f"Latest completed simulation date: {status.get('current_day','Not available')}(TMY simulation date, not the computer date)"
    estimate=status.get('estimated_remaining_hours')
    eta=f'Estimated radiation time remaining:  {estimate:.1f}  hours; excludes crop simulation and plotting and depends on actual speed.' if phase=='radiation' and isinstance(estimate,(int,float)) else ''
    log=HERE/('crops.log' if phase=='crops' else 'radiation.log')
    try:
        with log.open('rb') as f:
            size=log.stat().st_size;f.seek(max(0,size-9000));tail=f.read().decode('utf-8',errors='replace')
        tail='\n'.join(tail.splitlines()[-12:])
        modified=datetime.fromtimestamp(log.stat().st_mtime,ZoneInfo('Europe/Berlin')).strftime('%m-%d %H:%M:%S')
    except OSError:tail='No log available yet';modified='Not available'
    error=''
    if failed:
        failure=read(HERE/'pipeline_failure.json') or read(HERE/'failure.json')
        error='<pre>'+escape(failure.get('traceback',''))+'</pre>'
    blank='00_Blank_Tables/Thesis_Tables_PENDING.md'
    checkpoint_count=len(list((HERE/'radiation/fixed_tilt').glob('*/complete.json')))
    now=datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y-%m-%d %H:%M:%S %Z')
    nitrogen=read(HERE/'nitrogen_full_season/status.json')
    nsection=''
    preparation=read(HERE/'nitrogen_preparation.json')
    target=read(HERE/'target_resource_run/status.json')
    if preparation and not nitrogen and not target:
        nsection='<section><h2>: , </h2><p>Completed. Treatment; , . </p><a href="03_Notes/Nitrogen_Method_Review.md"></a></section>'
    if nitrogen:
        ndone=nitrogen.get('completed_point_seasons',0);ntotal=nitrogen.get('total_point_seasons',5412)
        nstate=nitrogen.get('status','unknown')
        nlive=alive(nitrogen.get('pid'))
        nlabel='Completed' if nstate=='complete' else 'Error' if nstate=='failed' else 'Running' if nlive else 'Process is not running; check the nitrogen log.'
        nsection=f'''<section><h2>: {escape(nlabel)}</h2><p>, ;  Aachen . ,  WLP81  NWLP, . </p>
<strong>{ndone} / {ntotal}  point crop seasons; {nitrogen.get('completed_cases',0)} / 36 Treatment</strong><progress value="{ndone}" max="{ntotal}"></progress>
<p>: {escape(nitrogen.get('updated_at',''))}</p><nav><a href="04_Nitrogen-/"></a><a href="../07_Full_Season_Run/nitrogen_full_season/status.json"></a></nav>
<pre>{escape(nitrogen.get('traceback','')) if nstate=='failed' else escape(str(nitrogen.get('active',[])))}</pre></section>'''
    if target:
        td=target.get('completed_managed_point_seasons',0);tt=target.get('total_managed_point_seasons',2706)
        ts=target.get('status');tlive=alive(target.get('pid'))
        label='Completed' if ts=='complete' else 'Packaging' if ts=='packaging' else 'Error' if ts=='failed' else 'Running' if tlive else ', '
        nsection=f'''<section><h2>, : {escape(label)}</h2>
<p>: , . BK50 + SoilGrids + , . </p>
<strong>{td} / {tt}  managed soil-column crop seasons; {target.get('completed_cases',0)} / {target.get('total_cases',18)} Treatment</strong><progress value="{td}" max="{tt}"></progress>
<p>Sampling pointPP81. Open field90%; , . </p>
<p>: {escape(target.get('updated_at',''))}</p><nav><a href="05_Target_Inputs/"></a><a href="../07_Full_Season_Run/target_resource_run/status.json"></a></nav>
<pre>{escape(target.get('traceback','')) if ts=='failed' else escape(str(target.get('active',[])))}</pre></section>'''
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="10">
<meta name="viewport" content="width=device-width,initial-scale=1"><title></title>
<style>body{{font:16px/1.7 'Segoe UI','Microsoft YaHei',sans-serif;background:#f1f5f9;color:#183047;margin:0}}main{{max-width:980px;margin:35px auto;padding:0 22px}}section{{background:white;padding:24px;border-radius:12px;margin:18px 0}}h1{{font-size:28px;margin:0}}h2{{font-size:19px;margin:0 0 8px}}.state{{font-size:23px;color:{'#b42318' if failed or not running and not complete else '#176b4a'};font-weight:650}}.muted{{color:#586b7b;font-size:14px}}progress{{width:100%;height:24px;accent-color:#247c9b}}pre{{white-space:pre-wrap;word-break:break-word;background:#102c3d;color:#d7eef5;padding:16px;border-radius:8px;font-size:12px}}a{{color:#0b6494}}nav{{display:flex;flex-wrap:wrap;gap:20px}}strong{{font-weight:650}}</style>
<main><h1></h1><p class="muted"> 10  · : {now}</p><p id="freshness" class="muted"></p>{nsection}
<section><div class="state">{state}</div><p> /  / Open field ·  · PP  WLP</p>
<h2>{title}</h2><strong>{count}({percent:.1f}%)</strong><progress value="{percent}" max="100"></progress>
<p>{escape(detail)}</p><p class="muted">{escape(eta)}</p><p class="muted">. , , . </p></section>
<section><h2></h2><nav><a href="01_Tables/"></a><a href="02_Figures/"></a><a href="{blank}"></a><a href="../07_Full_Season_Run/status.json"></a></nav>
<p> {checkpoint_count}  complete radiation-day blocks; completed  {summaries} / 36 Treatment. </p><p>{f"Final tables and  {export.get('figures',12)}  English figures exported." if complete else '. 121; , . '}</p></section>
<section><h2></h2><p>: {'Detected' if running else 'Not detected'} · Latest log update: {modified}</p>
<p class="muted">, . . </p><pre>{escape(tail)}</pre>{error}</section>
<section><h2></h2><p>. . SNOMIN. . </p><p>. , , PP/WLPCompleted. </p></section></main>
<script>const generatedAt={int(time.time()*1000)};function freshness(){{const age=Math.max(0,Math.floor((Date.now()-generatedAt)/1000));const el=document.getElementById('freshness');if(age>60){{el.textContent=' '+age+' ; , . . ';el.style.color='#b42318';}}}}freshness();setInterval(freshness,1000);</script></html>'''
    temp=PAGE.with_suffix('.tmp');temp.write_text(page,encoding='utf-8')
    # Windows browsers/previewers can briefly lock the HTML during a refresh.
    # Retry replacement without changing or interrupting the calculation job.
    for attempt in range(10):
        try:
            temp.replace(PAGE)
            break
        except PermissionError:
            if attempt==9:raise
            time.sleep(.2)
    return complete and (not nitrogen or nitrogen.get('status') in ('complete','failed')) and (not target or target.get('status') in ('complete','failed'))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    while True:
        try:
            complete=render()
            health=dict(status='running' if not complete else 'complete',pid=os.getpid(),
                last_success=datetime.now(ZoneInfo('Europe/Berlin')).isoformat(),last_error=None)
        except Exception as exc:
            # A display error must not permanently stop the monitor.
            complete=False
            health=dict(status='retrying',pid=os.getpid(),
                observed_at=datetime.now(ZoneInfo('Europe/Berlin')).isoformat(),last_error=repr(exc))
            print(health['observed_at'],repr(exc),file=sys.stderr,flush=True)
            if args.once:raise
        try:
            (HERE/'monitor_health.json').write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf-8')
        except OSError:pass
        if args.once or complete:break
        time.sleep(10)
