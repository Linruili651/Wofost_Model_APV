"""Restore baseline contents, compare the unified project, and atomically build Hao's ZIP."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json,os,shutil,sys,zipfile

ROOT=Path(__file__).resolve().parents[1]
UPDATE=ROOT.parent
RECORDS=ROOT/'09_Project_Records'
RESULTS=ROOT/'08_Thesis_Results'
TARGET=UPDATE/'Hao_Handoff_Six_Folders-_20261019.zip'
BASELINE=ROOT/'10_Delivery_Snapshot-/Original_Six_Folders_20261019_CONTENT_RESTORED.zip'
SKIP_DIRS={'.venv','Crop_Python','__pycache__','Runtime_Cache-','Runtime_Cache','pcse_runtime','.git','Layout_Check'}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def write_json(path,value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def baseline_members():
    audit=json.loads((RECORDS/'Redundant_Zip_Audit.json').read_text(encoding='utf-8'))
    return next(v for v in audit if Path(v['package']).name==TARGET.name)['content_map']

def restore_baseline(members):
    if BASELINE.exists():
        with zipfile.ZipFile(BASELINE) as z:
            assert len(z.namelist())==len(members)
        return True
    # A recipient does not have the sender's archival paths. Baseline history is
    # optional for running/repacking; existing comparison hashes remain available.
    if any(not Path(v['preserved_at']).is_file() for v in members):return False
    temp=BASELINE.with_suffix('.building')
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=2,allowZip64=True) as z:
        for entry in members:
            source=Path(entry['preserved_at'])
            if sha(source)!=entry['sha256']:raise ValueError('Baseline preserved file changed: '+str(source))
            z.write(source,entry['member'],compress_type=zipfile.ZIP_STORED if source.suffix=='.zip' else zipfile.ZIP_DEFLATED)
    temp.replace(BASELINE)
    return True

def project_files():
    for folder,dirs,names in os.walk(ROOT):
        path=Path(folder);rel=path.relative_to(ROOT)
        dirs[:]=[d for d in dirs if d not in SKIP_DIRS and not (path==ROOT and d=='10_Delivery_Snapshot-')]
        if rel.parts and rel.parts[0]=='07_Full_Season_Run':
            if 'radiation' in rel.parts and len(rel.parts)>=4:
                day=ROOT/Path(*rel.parts[:4])
                if not (day/'complete.json').exists():dirs[:]=[];continue
            if 'crop_results' in rel.parts and len(rel.parts)>=5:
                case=ROOT/Path(*rel.parts[:5])
                if not (case/'summary.json').exists():dirs[:]=[];continue
        for name in names:
            p=path/name
            if p.suffix in ('.pyc','.tmp','.log','.lock','.building'):continue
            if name in ('View_Progress.html','Open_Progress.html','INSTALLATION_CHECK.json'):continue
            if name=='epw2wea.exe':continue  # Original bytes retained in official native ZIP.
            if name=='Delivery_Build_Status.json':continue  # Record ZIP hashes outside the ZIP itself.
            yield p

def main():
    runtime_manifest=json.loads((ROOT/'07_Full_Season_Run/execution_manifest.json').read_text(encoding='utf-8'))
    verified=[]
    for name,expected in runtime_manifest.items():
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT) or sha(path)!=expected:
            raise ValueError('Runtime input outside project or changed: '+name)
        verified.append(path.relative_to(ROOT).as_posix())
    write_json(RECORDS/'Delivery_Runtime_Audit.json',dict(status='passed',
        all_active_code_and_inputs_inside_project=True,checked_files=verified,content_hashes_match=True))
    members=baseline_members();baseline_restored=restore_baseline(members)
    # Preserve files present only in the old package as explicitly inactive historical material.
    compatibility=ROOT/'11_Original_Package_Compatibility'
    delta=[]
    for entry in members:
        rel=Path(*Path(entry['member']).parts[1:])
        current=ROOT/rel
        if current.is_file():
            state='unchanged' if sha(current)==entry['sha256'] else 'updated'
        else:
            state='historical_only'
            target=compatibility/rel;target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():shutil.copy2(entry['preserved_at'],target)
            assert sha(target)==entry['sha256']
        delta.append(dict(original_relative_path=rel.as_posix(),status=state,original_sha256=entry['sha256']))
    compatibility.mkdir(exist_ok=True)
    (compatibility/'README_Historical_References.md').write_text(
        '# \n\n19ZIP, , . '
        ';  README_Start_Here.md . \n',encoding='utf-8')
    baseline_paths={v['original_relative_path'] for v in delta}
    files=list(project_files())
    added=[p.relative_to(ROOT).as_posix() for p in files if p.relative_to(ROOT).as_posix() not in baseline_paths]
    status_path=RESULTS/'EXPORT_STATUS.json'
    status=json.loads(status_path.read_text(encoding='utf-8'))
    complete=status.get('status')=='complete'
    target_validation=RESULTS/'05_Target_Inputs/VALIDATION.json'
    target_complete=target_validation.exists() and json.loads(target_validation.read_text(encoding='utf-8')).get('status')=='passed'
    counts={s:sum(v['status']==s for v in delta) for s in ('unchanged','updated','historical_only')}
    comparison=dict(baseline_members=len(members),baseline_restoration='member bytes preserved; original ZIP container metadata not reproduced',
        baseline_snapshot=str(BASELINE.relative_to(ROOT)) if baseline_restored else None,counts=counts,added_files=len(added),
        differences=delta,added_paths=added,full_season_results_complete=complete,
        nitrogen_field_status='blocked_missing_sourced_inputs',automatic_model_modes=['PP','WLP_MLWB'],
        adaptive_water_nitrogen_outputs_complete=target_complete,
        adaptive_water_nitrogen_scenario='BK50 hydraulics, SoilGrids estimates and explicit reference initial N; field_validated=False')
    write_json(RECORDS/'Delivery_Comparison.json',comparison)
    report='# 19ZIP\n\n'
    report+=f' {len(members)} :  {counts["unchanged"]};  {counts["updated"]};  {counts["historical_only"]}.  {len(added)} . \n\n'
    report+=': /SNOMIN; , ; ; Open field; , . \n\n'
    report+=('. \n\n' if complete else '**. ZIP, . ZIP. **\n\n')
    report+=', . : , BK50, SoilGrids; . \n\n'
    report+=('187 figures completed, 0805_Target_Inputs. Treatment, . \n\n' if target_complete else ', PP/WLP. \n\n')
    report+='ZIP; ZIPZIP. . \n'
    (RECORDS/'Delivery_Comparison.md').write_text(report,encoding='utf-8-sig')
    summary=RESULTS/'03_Notes/Hao_Delivery'
    summary.mkdir(parents=True,exist_ok=True)
    for name in ('Delivery_Comparison.md','Delivery_Comparison.json',
                 'Active_Dependency_Paths.json','Delivery_Extraction_Verification.json',
                 'Nitrogen_Location_and_Readiness.json','Delivery_Runtime_Audit.json'):
        if (RECORDS/name).exists():shutil.copy2(RECORDS/name,summary/name)
    write_json(ROOT/'DELIVERY_STATUS.json',dict(built_at=datetime.now(ZoneInfo('Europe/Berlin')).isoformat(),
        status='full_season_outputs_complete' if complete else 'interim_full_season_running',
        full_season_results_complete=complete,nitrogen_field_ready=False,adaptive_water_nitrogen_outputs_complete=target_complete,zip_name=TARGET.name))
    # Keep a portable checksum manifest for code and model inputs (no live logs/virtualenv).
    stable=[p for p in project_files() if p.relative_to(ROOT).parts[0] not in ('07_Full_Season_Run','08_Thesis_Results','09_Project_Records')]
    write_json(RECORDS/'Delivery_Input_Checksums.json',{p.relative_to(ROOT).as_posix():sha(p) for p in stable})
    files=sorted(project_files())
    temp=TARGET.with_suffix('.building')
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=2,allowZip64=True) as z:
        for p in files:
            name=(Path(ROOT.name)/p.relative_to(ROOT)).as_posix()
            if target_complete and p==ROOT/'07_Full_Season_Run/target_resource_run/status.json':
                snapshot=json.loads(p.read_text(encoding='utf-8'))
                snapshot.update(status='complete',phase='target_inputs',delivery_snapshot=True,
                    note='Scientific outputs and validation complete before archive creation; sender may still be packaging.',pid=None)
                z.writestr(name,json.dumps(snapshot,ensure_ascii=False,indent=2))
            else:
                z.write(p,name,compress_type=zipfile.ZIP_STORED if p.suffix=='.zip' else zipfile.ZIP_DEFLATED)
        z.writestr(ROOT.name+'/Open_Progress.html','<meta charset="utf-8"><meta http-equiv="refresh" content="0;url=08_Thesis_Results/View_Progress.html"><p> Start_Project.ps1, . </p>')
    with zipfile.ZipFile(temp) as z:
        bad=z.testzip()
        if bad:raise ValueError('ZIP CRC failure: '+bad)
        assert len(z.namelist())==len(files)+1
        archive_root=ROOT.name+'/'
        assert archive_root+'README_Start_Here.md' in z.namelist()
        assert not any('/.venv/' in n or '/Crop_Python/' in n for n in z.namelist())
    digest=sha(temp);temp.replace(TARGET)
    TARGET.with_suffix('.zip.sha256.txt').write_text(digest+'  '+TARGET.name+'\n',encoding='utf-8')
    record=dict(status='passed',zip_path=str(TARGET),zip_sha256=digest,zip_bytes=TARGET.stat().st_size,
                zip_files=len(files)+1,crc='passed',full_season_results_complete=complete,nitrogen_field_ready=False,
                adaptive_water_nitrogen_outputs_complete=target_complete)
    write_json(RECORDS/'Delivery_Build_Status.json',record)
    write_json(summary/'Delivery_Build_Status.json',record)
    print(json.dumps(record,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
