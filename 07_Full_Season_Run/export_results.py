"""Collect completed scientific tables/figures; keep blank thesis tables separate."""
from pathlib import Path
import csv, hashlib, json, shutil

HERE=Path(__file__).resolve().parent
from project_paths import RESULTS
DEST=RESULTS
CROPS=dict(winter_wheat='Winter wheat',spring_barley='Spring barley',grain_maize='Grain maize',
           potato='Potato',sugar_beet='Sugar beet',soybean='Soybean')
CASES=['open_field','fixed_tilt_conventional','fixed_tilt_semi_transparent']

def tables(rows=None):
    lines=['# Yield and seasonal evapotranspiration','',
           'Yield: t harvest-organ dry matter ha⁻¹. ET: mm, transpiration + soil evaporation.','',
           'Treatments: open field, fixed-tilt conventional opaque PV, fixed-tilt semi-transparent PV.','']
    if rows is None:
        lines += ['Results are pending. Empty cells indicate unavailable results and must not be interpreted as zero.','']
    lookup={} if rows is None else {(r['crop_id'],r['mode'],r['scenario_id']):r for r in rows}
    for mode in ('PP','WLP_MLWB'):
        lines += [f'## {"PP" if mode=="PP" else "WLP (layered soil)"}','',
            '| Crop | Open yield | Opaque PV yield | Semi-transparent PV yield | Open ET | Opaque PV ET | Semi-transparent PV ET |',
            '|---|---:|---:|---:|---:|---:|---:|']
        for crop,label in CROPS.items():
            cells=[]
            for metric in ('yield_t_DM_ha','et_mm'):
                for case in CASES:
                    r=lookup.get((crop,mode,case),{})
                    value=r.get(metric,'')
                    cells.append('' if value in ('',None) else f'{float(value):.2f}')
            lines.append('| '+label+' | '+' | '.join(cells)+' |')
        lines += ['']
    lines += ['Only fixed-tilt configurations are evaluated. Tracking and vertical systems are outside the study scope.',
              'Synthetic TMY scenario simulations; crop/soil/optical assumptions remain uncalibrated.',
              'ET is not irrigation requirement. Grain yield is withheld if any modelled point is not harvest-ready.','']
    return '\n'.join(lines)

def initialize():
    for name in ('00_Blank_Tables','01_Tables','02_Figures','03_Notes'):
        (DEST/name).mkdir(parents=True,exist_ok=True)
    blank=DEST/'00_Blank_Tables/Thesis_Tables_PENDING.md'
    if not blank.exists():blank.write_text(tables(),encoding='utf-8-sig')
    (DEST/'README.md').write_text(
        '# \n\n'
        ', Open field. \n\n'
        '- 00_Blank_Tables: , , . . \n'
        '- 01_Tables: , , . \n'
        '- 02_Figures: 12  1 ,  PNG, PDF, SVG. \n'
        '- 03_Notes: , . \n\n'
        '.  low  15×15 ; '
        '. \n\n'
        'EXPORT_STATUS.json  status=complete . . \n'
        ' ../07_Full_Season_Run/status.json. , . \n',encoding='utf-8-sig')
    for filename in ('Scope_and_Limitations_Fixed_Tilt.md','README_Methods_and_Execution.md'):
        if (HERE/filename).exists():shutil.copy2(HERE/filename,DEST/'03_Notes'/filename)
    if not (DEST/'EXPORT_STATUS.json').exists():
        (DEST/'EXPORT_STATUS.json').write_text(json.dumps(dict(status='pending_full_computation',figures_expected=13,
            comparison_rows_expected=36,blank_tables_available=True),indent=2),encoding='utf-8')

def main():
    initialize()
    metrics=HERE/'comparison_metrics.csv'
    if not metrics.exists():return
    rows=list(csv.DictReader(metrics.open(encoding='utf-8-sig',newline='')))
    expected={(c,m,s) for c in CROPS for m in ('PP','WLP_MLWB') for s in CASES}
    actual={(r['crop_id'],r['mode'],r['scenario_id']) for r in rows}
    if len(rows)!=36 or actual!=expected:raise ValueError('Incomplete final comparison table')
    summary_pending=(HERE/'SUMMARY_PLOT_HOLD').exists()
    if not summary_pending:
        from plot_relative_summary import build, STEM
        import pandas as pd
        build(pd.DataFrame(rows),HERE)
    images=[HERE/'figures'/f'{c}_{m}.{ext}' for c in CROPS for m in ('PP','WLP_MLWB') for ext in ('png','pdf','svg')]
    if not summary_pending:images += [HERE/'figures'/f'{STEM}.{ext}' for ext in ('png','pdf','svg')]
    if not all(p.is_file() for p in images):raise ValueError('Incomplete final figure set')
    sources=[(metrics,DEST/'01_Tables'/metrics.name)]
    if not summary_pending:
        sources += [(HERE/'normalised_yield_ET.csv',DEST/'01_Tables/normalised_yield_ET.csv'),
                    (HERE/'normalised_yield_ET_validation.json',DEST/'03_Notes/normalised_yield_ET_validation.json')]
    sources += [(p,DEST/'01_Tables'/name/p.relative_to(HERE/name))
                for name in ('radiation','crop_results') for p in (HERE/name).rglob('*.csv')]
    sources += [(p,DEST/'02_Figures'/p.name) for p in images]
    sources += [(HERE/'matched_daily_weather.csv',DEST/'01_Tables/matched_daily_weather.csv')]
    manifest=[]
    for source,target in sources:
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        manifest.append(dict(source=str(source),output=str(target.relative_to(DEST)),
                             sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    (DEST/'01_Tables/Thesis_Tables.md').write_text(tables(rows),encoding='utf-8-sig')
    (DEST/'03_Notes/Output_Manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (DEST/'EXPORT_STATUS.json').write_text(json.dumps(dict(status='complete',comparison_rows=36,figures=12 if summary_pending else 13,
        crop_specific_figures=12,summary_figures=0 if summary_pending else 1,summary_plot_pending=summary_pending,
        figure_files=len(images),copied_files=len(manifest),field_validated=False),indent=2),encoding='utf-8')
    # User requested the same Hao delivery ZIP to contain the completed outputs.
    import runpy
    runpy.run_path(str(HERE.parent/'09_Project_Records/build_hao_delivery.py'),run_name='__main__')

if __name__=='__main__':main()
