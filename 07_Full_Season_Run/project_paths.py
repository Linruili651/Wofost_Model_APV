"""Single project root and authoritative shared model loader."""
from pathlib import Path
import runpy

PROJECT=Path(__file__).resolve().parents[1]
PIPELINE=PROJECT/'07_Full_Season_Run'
RESULTS=PROJECT/'08_Thesis_Results'
TIANZE=PROJECT/'05_Tianze_Files'
WEATHER=PROJECT/'03_Precipitation/Aachen_TMY_Weather.epw'
CORE=PROJECT/'06_Hao_Interface_and_Rerun/Shared_Core'

def load_crop():
    registry=runpy.run_path(str(CORE/'Module_Loader.py'))
    return registry['install']()

def manifest_files():
    files=[PIPELINE/n for n in ('run_radiation.py','run_crops_and_plots.py','export_results.py','project_paths.py','plot_relative_summary.py')]
    files+=list(CORE.glob('*.py'))
    files+=list((PROJECT/'06_Hao_Interface_and_Rerun/Shared_Inputs').rglob('*.json'))
    files+=list((PROJECT/'06_Hao_Interface_and_Rerun/Shared_Inputs').rglob('*.yaml'))
    files+=list((PROJECT/'04_Soil_and_Python/Soil_Inputs').glob('*.json'))
    files+=[WEATHER,PROJECT/'03_Precipitation/Precipitation_Supplement.json',
            PROJECT/'03_Precipitation/Precipitation_Adapter.py',
            TIANZE/'Three_Radiation_Notebooks/Original_Notebooks/fixed_tilt.ipynb',
            TIANZE/'Radiance_Runtime/runtime_env.py']
    return sorted(set(files))
