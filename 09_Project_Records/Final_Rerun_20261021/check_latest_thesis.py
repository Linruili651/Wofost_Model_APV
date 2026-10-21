from pathlib import Path
import zipfile,xml.etree.ElementTree as ET,json,re,hashlib
import pandas as pd
A=Path(__file__).resolve().parent;P=A.parents[1].parent/'Thesis_Linrui.docx'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
with zipfile.ZipFile(P) as z:root=ET.fromstring(z.read('word/document.xml'))
body=list(root.find('w:body',ns))
def text(el):return ''.join(n.text or '' for n in el.findall('.//w:t',ns))
def rows(el):return [[text(c).strip() for c in tr.findall('w:tc',ns)] for tr in el.findall('w:tr',ns)]
captions={}
for i,el in enumerate(body):
    if el.tag.endswith('}p'):
        t=text(el)
        m=re.match(r'Table\s+(3-(?:12|13|14|15|16|17)|A-14)\b',t)
        if m and m[1] not in captions:
            for following in body[i+1:]:
                if following.tag.endswith('}tbl'):captions[m[1]]=rows(following);break
                if following.tag.endswith('}p') and text(following).strip():break
crops=['winter_wheat','spring_barley','grain_maize','potato','sugar_beet','soybean']
cases={'Open field':'open_field','Conventional PV':'fixed_tilt_conventional','Semi-transparent PV':'fixed_tilt_semi_transparent'}
main=pd.read_csv(A/'pp/comparison_metrics.csv',float_precision='round_trip').set_index(['crop_id','mode','scenario_id'])
normal=pd.read_csv(A/'pp/normalised_yield_ET.csv',float_precision='round_trip').set_index(['crop_id','mode','scenario_id'])
checks=[]
def check_value(label,observed,expected):
    observed=observed.strip().replace('−','-');value=float(observed)
    decimals=len(observed.split('.')[1]) if '.' in observed else 0
    tol=.5*10**(-decimals)+1e-10
    checks.append(dict(cell=label,thesis_value=value,rerun_value=float(expected),display_decimals=decimals,passed=bool(abs(value-expected)<=tol)))
for number,crop in enumerate(crops,12):
    table=captions[f'3-{number}'];assert len(table)==7 and len(table[0])==8
    for row in table[1:]:
        mode='PP' if row[0]=='PP' else 'WLP_MLWB';case=cases[row[1]];key=(crop,mode,case)
        expected=[main.loc[key,k] for k in ['yield_t_DM_ha','transpiration_mm','soil_evaporation_mm','et_mm']]
        expected += [normal.loc[key,k] for k in ['relative_yield','relative_et']]
        for j,(obs,val) in enumerate(zip(row[2:],expected)):check_value(f'3-{number}/{mode}/{case}/{j}',obs,val)
managed=pd.read_csv(A/'08_Thesis_Results/05_Target_Inputs/01_Tables/Managed_Water_Nitrogen_Comparison.csv',float_precision='round_trip').set_index(['crop_id','scenario_id'])
names={'Winter wheat':'winter_wheat','Spring barley':'spring_barley','Grain maize':'grain_maize','Potato':'potato','Sugar beet':'sugar_beet','Soybean':'soybean'}
table=captions['A-14'];assert len(table)==19 and len(table[0])==7
for row in table[1:]:
    key=(names[row[0]],cases[row[1]])
    for j,metric in enumerate(['yield_t_DM_ha','et_mm','net_irrigation_mm','fertiliser_N_kg_ha','nitrogen_leaching_kg_N_ha']):
        check_value(f'A-14/{key[0]}/{key[1]}/{metric}',row[j+2],managed.loc[key,metric])
result=dict(status='passed' if all(c['passed'] for c in checks) else 'differences_found',main_cases=36,managed_cases=18,
    numeric_cells_checked=len(checks),failed_cells=[c for c in checks if not c['passed']],
    method='Compare each printed number with fresh rerun allowing only its stated display rounding',
    latest_paper_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),checks=checks)
(A/'latest_thesis_table_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=True,indent=2))
assert result['status']=='passed'
