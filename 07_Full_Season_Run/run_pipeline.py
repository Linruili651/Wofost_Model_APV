"""Local background supervisor; fail closed, persist logs, resume checkpoints."""
from pathlib import Path
import os, sys, subprocess, json, hashlib, time, traceback
HERE=Path(__file__).resolve().parent
from project_paths import PROJECT, TIANZE, manifest_files
RADIATION=TIANZE/'Radiance_Runtime/.venv/Scripts/python.exe'
CROP=PROJECT/'00_Runtime/Crop_Python/Scripts/python.exe'

def save(name,obj):
    (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    lock=HERE/'pipeline.lock'
    with lock.open('x') as f:f.write(str(os.getpid()))
    try:
        files=manifest_files()
        manifest={p.relative_to(PROJECT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        old=HERE/'execution_manifest.json'
        if old.exists():
            previous=json.loads(old.read_text(encoding='utf-8'))
            normalised={}
            for name,value in previous.items():
                path=Path(name)
                if path.is_absolute():
                    parts=path.parts
                    if PROJECT.name not in parts:raise RuntimeError('Manifest has an unrelated external path')
                    name=Path(*parts[parts.index(PROJECT.name)+1:]).as_posix()
                normalised[name]=value
            if normalised!=manifest:
                raise RuntimeError('Inputs or scripts changed: review before reusing checkpoints')
        save('execution_manifest.json',manifest)
        save('pipeline_process.json',dict(pid=os.getpid(),status='running',started=time.strftime('%Y-%m-%d %H:%M:%S')))
        env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUNBUFFERED='1')
        for executable,script,log in [(RADIATION,'run_radiation.py','radiation.log'),(CROP,'run_crops_and_plots.py','crops.log')]:
            with (HERE/log).open('a',encoding='utf-8') as stream:
                subprocess.run([str(executable),str(HERE/script)],cwd=HERE,stdout=stream,stderr=subprocess.STDOUT,env=env,check=True)
        save('pipeline_process.json',dict(pid=os.getpid(),status='complete',finished=time.strftime('%Y-%m-%d %H:%M:%S')))
    except Exception:
        save('pipeline_failure.json',dict(status='failed',traceback=traceback.format_exc()))
        save('pipeline_process.json',dict(pid=os.getpid(),status='failed'))
        raise
    finally:
        lock.unlink(missing_ok=True)
