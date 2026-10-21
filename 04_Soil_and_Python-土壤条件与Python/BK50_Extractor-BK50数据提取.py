"""Extract a chosen BK50 soil unit and ONP rows; never silently select a field for the user."""

# Load bilingual file paths through stable internal Python module names.
from pathlib import Path as _Path
import runpy as _runpy
_package_root = next(p for p in _Path(__file__).resolve().parents if (p / '06_Hao_Interface_and_Rerun-Hao接口与复跑').is_dir())
_registry = _runpy.run_path(str(_package_root / '06_Hao_Interface_and_Rerun-Hao接口与复跑/Shared_Core-共享核心/Module_Loader-模块加载.py'))
_registry["install"]()
from pathlib import Path
import argparse
import hashlib
import json
import sqlite3
import zipfile

ROOT=_package_root


def extract(unit, unpacked=None, output=None):
    import openpyxl
    unpacked=Path(unpacked or ROOT/"04_Soil_and_Python-土壤条件与Python/Unpacked_Database-解压数据库").resolve()
    archive_path=ROOT/"04_Soil_and_Python-土壤条件与Python/BK50_Official_Database-BK50官方数据库.zip"
    database=unpacked/"BK50_GPKG/BK50_A.gpkg"
    onp=unpacked/"Tabellen_Erlaeuterungen/Tabelle_ONP.xlsx"
    if not database.exists() or not onp.exists():
        source=json.loads((ROOT/"04_Soil_and_Python-土壤条件与Python/Database_Source-数据库来源.json").read_text(encoding="utf-8"))
        with archive_path.open("rb") as f:
            actual=hashlib.file_digest(f,"sha256").hexdigest()
        if actual!=source["sha256"]:raise ValueError("Official archive SHA-256 mismatch")
        with zipfile.ZipFile(archive_path) as archive:
            for name in ["BK50_GPKG/BK50_A.gpkg","Tabellen_Erlaeuterungen/Tabelle_ONP.xlsx"]:
                archive.extract(name,unpacked)
    c=sqlite3.connect(database.as_uri()+"?mode=ro",uri=True);c.row_factory=sqlite3.Row
    features=c.execute('SELECT fid,Name,GW_CODE,SW_CODE,TIEFE,FK,NFK,LK,KF,TYP_TEXT FROM BK50 WHERE Name=?',(unit,)).fetchall()
    c.close()
    if not features:raise ValueError(f"Soil unit not present: {unit}")
    wb=openpyxl.load_workbook(onp,read_only=True,data_only=True)
    rows=wb.worksheets[0].iter_rows(values_only=True);headers=next(rows)
    selected=[dict(zip(headers,r)) for r in rows if r[1]==unit];wb.close()
    if not selected:raise ValueError("No matching ONP rows; do not fabricate a profile")
    result=dict(status="EXPLICITLY_SELECTED_MAP_UNIT_REQUIRES_FIELD_AND_HYDRAULIC_REVIEW",
        source_table="Tabellen_Erlaeuterungen/Tabelle_ONP.xlsx",
        source_onp_sha256=hashlib.sha256(onp.read_bytes()).hexdigest(),
        selected_map_feature=dict(features[0]),map_feature_count_with_same_unit=len(features),rows=selected,
        note="The same soil unit occurs in several polygons; selecting a code does not establish which polygon is the actual field.")
    target=Path(output or ROOT/"04_Soil_and_Python-土壤条件与Python/Soil_Inputs-土壤输入/Selected_ONP_Review-待复核土层.json")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return target


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--unit",required=True,help="Exact Name field, e.g. L5102_K342; choose from the actual field's polygon")
    p.add_argument("--unpacked",type=Path)
    p.add_argument("--output",type=Path)
    args=p.parse_args();print(extract(args.unit,args.unpacked,args.output))
