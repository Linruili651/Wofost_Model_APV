"""Preserve every ZIP member before proposing removal of redundant old packages."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1]
UPDATE=ROOT.parent
ARCHIVE=UPDATE/'_Archive-'
CACHE={}

def sha(path):
    key=str(path)
    if key not in CACHE:
        h=hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        CACHE[key]=h.hexdigest()
    return CACHE[key]

def main():
    by_size={}
    for base in (ROOT,ARCHIVE):
        for p in base.rglob('*'):
            if not p.is_file() or any(x in p.parts for x in ('.venv','Crop_Python','__pycache__')):continue
            by_size.setdefault(p.stat().st_size,[]).append(p)
    report=[]
    for package in sorted(UPDATE.glob('*.zip')):
        if package.name in ('skills.zip','Hao_Handoff_Water_Nitrogen-_20261020.zip'):continue
        records=[]
        with zipfile.ZipFile(package) as z:
            for member in z.infolist():
                if member.is_dir():continue
                relative=Path(member.filename.replace('\\','/'))
                if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe ZIP path')
                digest=hashlib.sha256()
                with z.open(member) as f:
                    for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
                value=digest.hexdigest()
                candidates=by_size.get(member.file_size,[])
                candidates=sorted(candidates,key=lambda p:p.name!=relative.name)
                kept=next((p for p in candidates if sha(p)==value),None)
                if kept is None:
                    kept=ARCHIVE/'Unique_Zip_Contents-'/package.stem/relative
                    kept.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(member) as source,kept.open('wb') as target:shutil.copyfileobj(source,target)
                    if sha(kept)!=value:raise ValueError('Extracted content checksum failed')
                    by_size.setdefault(member.file_size,[]).append(kept)
                records.append(dict(member=member.filename,sha256=value,preserved_at=str(kept)))
        report.append(dict(package=str(package),package_sha256=sha(package),bytes=package.stat().st_size,
                           members=len(records),all_members_preserved=True,content_map=records))
        print('VERIFIED',package.name,len(records),flush=True)
    output=ROOT/'09_Project_Records/Redundant_Zip_Audit.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('AUDIT COMPLETE',len(report),'ZIPs',sum(r['bytes'] for r in report),flush=True)

if __name__=='__main__':main()
