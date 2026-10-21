"""Project-local native Radiance setup for Tianze's Aachen models."""
from pathlib import Path
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
TOOLS = ('rtrace', 'oconv', 'genbox', 'xform', 'gendaylit', 'gencumulativesky')


def configure():
    import bifacial_radiance as br
    source = HERE / 'Radiance_6.0.2'
    record = json.loads((HERE/'DOWNLOAD_SOURCE-下载来源.json').read_text(encoding='utf-8'))
    # Radiance library lookup in old Windows code is sensitive to Unicode paths.
    # Keep the downloaded original here, and use a dedicated ASCII execution copy.
    target = Path(tempfile.gettempdir()) / ('Tianze_Aachen_Radiance_' + record['sha256'][:12])
    marker = target / 'SOURCE_SHA256.txt'
    ready = marker.exists() and marker.read_text(encoding='ascii').strip() == record['sha256']
    ready = ready and all((target/'bin'/f'{n}.exe').is_file() for n in TOOLS if n!='gencumulativesky')
    if not ready:
        shutil.copytree(source,target,dirs_exist_ok=True)
        marker.write_text(record['sha256']+'\n',encoding='ascii')
    bundled = Path(br.__file__).resolve().parent/'data'
    os.environ['PATH'] = os.pathsep.join([str(target/'bin'),str(bundled),os.environ.get('PATH','')])
    os.environ['RAYPATH'] = os.pathsep.join(['.',str(target/'lib')])
    programs = {n:shutil.which(n) for n in TOOLS}
    if not all(programs.values()):
        raise RuntimeError(f'Missing native tools: {programs}')
    return target,programs


def check():
    home,programs=configure()
    proc=subprocess.run([programs['rtrace'],'-version'],capture_output=True,text=True,timeout=30)
    if proc.returncode:
        raise RuntimeError(proc.stderr)
    report=dict(date='2026-10-19',scope='Aachen Tianze radiation only',
        python=sys.executable,python_version=sys.version,
        packages={n:importlib.metadata.version(n) for n in ('bifacial-radiance','pvlib','numpy','pandas')},
        downloaded_native_root=str(HERE/'Radiance_6.0.2'),execution_native_root=str(home),
        programs=programs,rtrace_version=proc.stdout.strip(),rtrace_exit_code=proc.returncode,
        path_configuration='current process and children; no permanent system PATH changes')
    (HERE/'INSTALLATION_CHECK-安装检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    return report


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    check()
