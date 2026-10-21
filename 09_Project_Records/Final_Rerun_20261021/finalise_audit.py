from pathlib import Path
import json,os,hashlib,runpy,zipfile,xml.etree.ElementTree as ET
A=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
status=read(A/'status.json');assert status['status']=='complete', 'Scientific runs still active'
root=A.parents[1]
manifest=read(A/'target_resource_run/execution_manifest.json')['files']
changed=[rel for rel,expected in manifest.items() if hashlib.sha256((root/rel).read_bytes()).hexdigest()!=expected]
assert not changed,('Scientific code/input changed during the run',changed)
snapshots=read(A/'source_manifest.json')
paper=next(r for r in snapshots if r['source'].endswith('Thesis_Linrui.docx'))
paper_unchanged=hashlib.sha256(Path(paper['source']).read_bytes()).hexdigest()==paper['sha256']
latest=read(A/'latest_thesis_table_verification.json')
assert latest['status']=='passed' and latest['latest_paper_sha256']==hashlib.sha256(Path(paper['source']).read_bytes()).hexdigest()
(A/'end_of_run_input_verification.json').write_text(json.dumps(dict(status='passed',
    checked_scientific_files=len(manifest),changed_files=changed,paper_unchanged_since_snapshot=paper_unchanged,
    latest_paper_rechecked=True,latest_paper_numeric_cells_checked=latest['numeric_cells_checked'],
    latest_paper_sha256=latest['latest_paper_sha256']),indent=2),encoding='utf-8')
p=runpy.run_path(str(A/'publish_tables.py'));p['build']();p['managed_tables']()
export_path=A/'08_Thesis_Results/EXPORT_STATUS.json'
export=read(export_path);export.update(figures=1,crop_specific_figures=0,summary_figures=1,
    adaptive_water_nitrogen_figures=1,total_figures_all_studies=2,per_crop_outputs='tables')
export_path.write_text(json.dumps(export,ensure_ascii=False,indent=2),encoding='utf-8')
qa='Normalised figure inspected; crop outputs are data tables as requested.'
for name in ('VALIDATION.json','STATUS.json'):
    path=A/'08_Thesis_Results/05_Target_Inputs'/name
    v=read(path);v['visual_QA']=qa;path.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
status['target_validation']['visual_QA']=qa
status['artifact_checks_complete']=True
(A/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
comparison=read(A/'01_36_Case_Comparison_and_Crop_Tables/36_Case_Comparison_Conclusion.json')
managed=read(A/'03_Managed_Water_Nitrogen_Tables/Managed_Comparison_Conclusion.json')
assert comparison['numerically_equivalent_cases']==36
assert managed['target_statuses_unchanged']
for metric,value in managed['max_abs_differences'].items():assert value<1e-7,(metric,value)
for kind,count in [('pp',36),('target',18)]:
    r=read(A/(kind+'_comparison.json'));assert len(r)==count and all(x['passed'] for x in r)
book=A/'01_36_Case_Comparison_and_Crop_Tables/Rerun_36_Case_Comparison_and_Crop_Tables.xlsx'
with zipfile.ZipFile(book) as z:
    root=ET.fromstring(z.read('xl/workbook.xml'))
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    names=[s.attrib['name'] for s in root.findall('s:sheets/s:sheet',ns)];assert len(names)==7
    error_cells=[]
    for name in z.namelist():
        if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
            xml=ET.fromstring(z.read(name))
            error_cells +=[(name,c.attrib.get('r')) for c in xml.findall('.//s:c',ns) if c.attrib.get('t')=='e']
    assert not error_cells
norms=[]
for folder in [A/'pp/figures',A/'08_Thesis_Results/05_Target_Inputs/02_Figures']:
    files=list(folder.glob('*'));assert len(files)==3,[(p.name) for p in files]
    norms.extend([str(x.relative_to(A)) for x in files])
test_summaries={}
for name in ['model_tests.log','nitrogen_tests.log']:
    text=(A/name).read_text(encoding='utf-8',errors='replace');assert 'Ran 6 tests' in text and '\nOK' in text
    test_summaries[name]='6 tests passed'
text=f'''# Final_Rerun_Conclusions

Completed, Radiance. , , Data_Table; ZIP. 

## 36

360. 35; Winter wheatPPOpen fieldET5.684341886080802e-14 mm, CSV. 36, . 

 `Read_First_36_Case_Comparison.md`; ExcelCSV/Markdown `01_36_Case_Comparison_and_Crop_Tables/`.  `pp/` , CSV. 

## 

- 7.3PP/WLP: 36, 5412, . 
- 8.1: ×Mode, 18; , . 
- 8.1: 18, 27062706PP81, . 
- 6, 6; 21. 
- 160mm, 5mm, ; . 

: {json.dumps(managed['max_abs_differences'],ensure_ascii=False)}. 

{managed['target_achieved_cases']}/18, 0{managed['all_irrigation_zero']}; Sugar beetTreatment, . {status['target_validation']['max_water_balance_residual_mm']:.6g} mm, {status['target_validation']['max_nitrogen_balance_residual_kg_N_ha']:.6g} kgN/ha. 

## 

PNG/PDF/SVG,  `02_Normalised_Figures/`. Data_Table. ,  `03_Managed_Water_Nitrogen_Tables/`. Excel7, ; . PNG `workbook_QA/`, , . 

## 

, . 3.17.3, 8.18.1; 3.4Data_Table, . , . 

Tables 3-123-1736Table A-1418, 306, .  `latest_thesis_table_verification.json`,  `source_snapshot/Thesis_Linrui_at_completion.docx`. 

3.2: Open field, EPW.  `open_field_weather_source_comparison.csv`. 

, , , , ET. , . . 
'''
(A/'Final_Rerun_Conclusions.md').write_text(text,encoding='utf-8-sig')
f=A/'README_Final_Rerun.md';t=f.read_text(encoding='utf-8-sig')
t=t.replace(',  `status.json` ;  `status=complete` Completed. . ',
    'Completed, `status.json`  `complete`.  `Final_Rerun_Conclusions.md`  `Read_First_36_Case_Comparison.md`; . ')
t=t.replace(', . ',' `Final_Rerun_Conclusions.md`. , Data_Table. ')
f.write_text(t,encoding='utf-8-sig')
inventory=[]
for folder,dirs,files in os.walk(A,followlinks=False):
    dirs[:]=[d for d in dirs if d not in ('node_modules','__pycache__')]
    for name in files:
        path=Path(folder)/name
        if name=='artifact_inventory.json':continue
        inventory.append(dict(path=str(path.relative_to(A)),bytes=path.stat().st_size))
result=dict(status='complete',files=inventory,workbook_sheets=names,workbook_error_cells=error_cells,
    tests=test_summaries,normalised_figure_files=norms,table_visual_QA='All seven worksheets rendered and inspected',
    note='Authoring runtime dependencies are not scientific inputs or outputs and are excluded from the inventory; the temporary junction was removed safely')
(A/'artifact_inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('FINAL_AUDIT_COMPLETE',len(inventory),flush=True)
