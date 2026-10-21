"""Checkpointed ground-only Tianze runs; originals remain unchanged."""
from pathlib import Path
from dataclasses import replace, asdict
import argparse, hashlib, json, os, sys, time, types, traceback
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
from project_paths import PROJECT, TIANZE, WEATHER
PART = TIANZE
ENGINE = PROJECT
sys.path.insert(0, str(PART/'Radiance_Runtime'))
from runtime_env import configure
configure()
MODELS = ('fixed_tilt',)
LABELS = ('Fixed_tilt',)
GRID = dict(x_min=-16., x_max=16., y_min=-16., y_max=16., nx=15, ny=15, z_m=.05)

def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str, allow_nan=False), encoding='utf-8')
    tmp.replace(path)

def load_model(stem):
    label = LABELS[MODELS.index(stem)]
    source = PART/f'Three_Radiation_Notebooks/Original_Notebooks/{stem}.ipynb'
    nb = json.loads(source.read_text(encoding='utf-8'))
    module = types.ModuleType('tianze_'+stem); sys.modules[module.__name__] = module
    ns = module.__dict__
    # Only definition/input cells, never the original execution cell.
    for cell in nb['cells']:
        if cell['cell_type'] != 'code': continue
        code = ''.join(cell['source'])
        if 'hao_hourly, ground_summary = model_for_optimization(' in code: break
        if 'return hour_starts, sampling_times, metdata, timing' in code:
            needle = '    return hour_starts, sampling_times, metdata, timing'
            assert code.count(needle) == 1
            code = code.replace(needle, '    globals()["captured_weather"] = selected.copy()\n'+needle)
        exec(compile(code, str(source), 'exec'), ns)
    ns['WEATHER_DIRECTORY'] = WEATHER.parent
    ns['SETTINGS'] = replace(ns['SETTINGS'], n_workers=2)
    return ns, source

def run_day(ns, stem, day, out, pilot=False):
    out.mkdir(parents=True, exist_ok=True)
    start = f'{day} 12:00' if pilot else str(day)
    end = f'{day} 13:00' if pilot else str(day)
    scenario = replace(ns['scenario'], start_date=start, end_date=end,
                       scenario_name=f'{stem}_{day}', weather_filename=WEATHER.name,
                       ground_grid_x=GRID['nx'], ground_grid_y=GRID['ny'])
    dx = (GRID['x_max']-GRID['x_min'])/GRID['nx']; dy = (GRID['y_max']-GRID['y_min'])/GRID['ny']
    scan = dict(xstart=GRID['x_min']+dx/2, ystart=GRID['y_min']+dy/2, zstart=GRID['z_m'],
                sx_xinc=dx, sx_yinc=0., sx_zinc=0., xinc=0., yinc=dy, zinc=0.,
                Nx=GRID['nx'], Ny=GRID['ny'], Nz=1, orient='0 0 -1')
    ns['make_shared_ground_scan'] = lambda *args: (scan, dx*dy)
    captured = []
    def ground(octfile, simulation_name, scan, cell_area_m2, analysis_name):
        analysis = ns['br'].AnalysisObj(octfile, simulation_name, hpc=ns['SETTINGS'].hpc)
        full = analysis.analysis(octfile, analysis_name, scan, accuracy=ns['SETTINGS'].accuracy)
        total = np.asarray(full['Wm2'], dtype=float)
        direct = ns['trace_direct_ground_irradiation'](analysis, octfile, scan)
        if len(total) != 225 or not np.isfinite(total).all() or (total < 0).any():
            raise ValueError('Invalid ground point irradiance')
        panel = 'semi_transparent' if 'semi_transparent' in analysis_name else 'conventional'
        # Save hourly point values before the native temporary directory disappears.
        captured.append((panel, total.copy(), direct.copy()))
        return np.array([direct.sum(), (total-direct).sum(), total.sum()])*cell_area_m2
    ns['analyze_ground_hour'] = ground
    ns['RESULTS_DIRECTORY'] = out
    ns['LINRUI_RESULTS_FILE'] = out/'original_period_totals.csv'
    ns['HAO_RESULTS_FILE'] = out/'unused_panel_output.csv'
    started = time.time()
    _, totals = ns['model_for_optimization'](ns['candidate_design'], scenario,
                 ns['module_specification'], ns['array_specification'], calculate_linrui=True, calculate_hao=False)
    weather = ns['captured_weather']
    expected = int((weather.GHI > 0).sum())
    rows = []
    for panel in ('conventional', 'semi_transparent'):
        data = [v for v in captured if v[0] == panel]
        if len(data) != expected: raise ValueError('Missing or duplicate irradiated hours')
        total = np.sum([v[1] for v in data], axis=0) if data else np.zeros(225)
        direct = np.sum([v[2] for v in data], axis=0) if data else np.zeros(225)
        integrated = float(total.sum()*dx*dy)
        if not np.isclose(integrated, totals[panel]['ground_total_incident_energy_Wh_period'], rtol=1e-10):
            raise ValueError('Point/day and original period integral disagree')
        for i in range(15):
            for j in range(15):
                k = i*15+j
                rows.append(dict(day=str(day),scenario_id=stem+'_'+panel,point_id=f'p{i:03d}_{j:03d}',
                    x_m=GRID['x_min']+(i+.5)*dx,y_m=GRID['y_min']+(j+.5)*dy,cell_area_m2=dx*dy,
                    total_Wh_m2_day=total[k],direct_Wh_m2_day=direct[k],
                    diffuse_residual_Wh_m2_day=total[k]-direct[k]))
    pd.DataFrame(rows).to_csv(out/'ground_daily.csv',index=False)
    weather.to_csv(out/'hourly_weather.csv',index_label='hour_end')
    record = dict(status='passed',day=str(day),mounting=stem,pilot=pilot,hours=len(weather),
                  irradiated_hours=expected,elapsed_seconds=time.time()-started,
                  original_period_totals=totals,ground_points=225,common_area_m2=1024,
                  geometry=asdict(ns['candidate_design']),array=asdict(ns['array_specification']),
                  module=asdict(ns['module_specification']),settings=asdict(ns['SETTINGS']))
    return record

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--pilot',action='store_true'); args = ap.parse_args()
    dates = [pd.Timestamp('2002-06-21').date()] if args.pilot else list(pd.date_range('2001-10-15','2002-10-31').date)
    phase = 'pilot' if args.pilot else 'radiation'
    write_json(HERE/'grid.json',GRID)
    total = len(dates)*len(MODELS); done = 0; durations = []
    for stem in MODELS:
        ns, source = load_model(stem)
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        for day in dates:
            out = HERE/phase/stem/str(day)
            marker = out/'complete.json'
            if marker.exists():
                record = json.loads(marker.read_text(encoding='utf-8'))
                if record['source_sha256'] != sha: raise ValueError('Source changed since checkpoint')
            else:
                record = run_day(ns,stem,day,out,args.pilot)
                record['source_sha256'] = sha
                write_json(marker,record)
            done += 1; durations.append(record['elapsed_seconds'])
            write_json(HERE/'status.json',dict(phase=phase,status='running',completed_days=done,total_days=total,
                      current_model=stem,current_day=str(day),mean_seconds_per_day=float(np.mean(durations)),
                      estimated_remaining_hours=float(np.mean(durations)*(total-done)/3600)))
            print('CHECKPOINT',stem,day,f'{done}/{total}',flush=True)
    write_json(HERE/(phase+'_complete.json'),dict(status='complete',days_per_mounting=len(dates),
        cases=2,pilot=args.pilot,completed_at=time.strftime('%Y-%m-%d %H:%M:%S')))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try: main()
    except Exception:
        write_json(HERE/'failure.json',dict(status='failed',traceback=traceback.format_exc()))
        raise
