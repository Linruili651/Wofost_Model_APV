"""Read Tianze's existing Linrui ground CSVs without running Radiance.

The source fields are land-integrated, period-integrated Wh. This reader splits
the two construction branches; it does not fabricate daily or pointwise input.
"""
from pathlib import Path
import argparse
import csv
import math

PANELS = ('conventional', 'semi_transparent')
COMPONENTS = ('direct','diffuse','total')


def read_ground_csv(path, mounting):
    """Return two long-form construction rows per complete source scenario row."""
    path=Path(path)
    result=[]
    with path.open(encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle)
        fields=set(reader.fieldnames or [])
        branches=[p for p in PANELS if f'{p}_ground_total_incident_energy_Wh_period' in fields]
        if not branches:
            raise ValueError('No Linrui ground fields found. Hao panel-face columns are not ground input.')
        for index,row in enumerate(reader,start=2):
            for panel in branches:
                names={c:f'{panel}_ground_{c}_incident_energy_Wh_period' for c in COMPONENTS}
                if not all(n in fields for n in names.values()):
                    raise ValueError(f'{panel}: missing direct/diffuse/total columns')
                values=[row.get(names[c],'').strip() for c in COMPONENTS]
                if all(v=='' for v in values):continue  # Historical appended row with output not enabled.
                try:
                    energy={c:float(row[names[c]]) for c in COMPONENTS}
                except (ValueError,TypeError) as exc:
                    raise ValueError(f'Incomplete ground values in source line {index}, {panel}') from exc
                if not all(math.isfinite(v) and v>=0 for v in energy.values()):
                    raise ValueError(f'Invalid or negative ground values at line {index}')
                if not math.isclose(energy['direct']+energy['diffuse'],energy['total'],rel_tol=1e-6,abs_tol=1e-6):
                    raise ValueError(f'Ground direct+diffuse != total at line {index}')
                result.append(dict(mounting=mounting,panel_type=panel,
                    scenario_name=row.get('scenario_name',''),run_id=row.get('run_id',''),
                    period_start=row.get('period_start',''),period_end=row.get('period_end',''),
                    weather_filename=row.get('weather_filename',''),
                    ground_direct_Wh_period=energy['direct'],ground_diffuse_Wh_period=energy['diffuse'],
                    ground_total_Wh_period=energy['total'],
                    quantity='land-integrated incident energy over selected period',unit='Wh',
                    daily_per_area_input_ready=False,source_file=str(path.resolve()),source_line=index))
    if not result:raise ValueError('Ground columns exist but no complete ground data rows were found.')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_file',type=Path)
    parser.add_argument('--mounting',required=True,choices=['fixed_tilt','single_axis','vertical_pv'])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    rows=read_ground_csv(args.csv_file,args.mounting)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print(f'Read {len(rows)} construction records; output remains period-integrated ground energy, not daily irradiance.')


if __name__=='__main__':main()
