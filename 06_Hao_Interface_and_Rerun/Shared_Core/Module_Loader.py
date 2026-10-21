"""Resolve English-Chinese filenames to stable internal Python module identifiers."""
from pathlib import Path
import importlib.util
import sys
import types
ROOT=Path(__file__).resolve().parents[2]
MODULES={'nitrogen_engine': '06_Hao_Interface_and_Rerun/Shared_Core/Nitrogen_Engine.py', 'legacy_bridge': '06_Hao_Interface_and_Rerun/Shared_Core/Weather_and_Grid_Utilities.py', 'precipitation_adapter': '03_Precipitation/Precipitation_Adapter.py', 'crop_engine': '06_Hao_Interface_and_Rerun/Shared_Core/Crop_Engine.py', 'radiation_bridge': '05_Tianze_Files/Python_Adapters/Radiation_Bridge.py', 'tianze_fixed': '05_Tianze_Files/Python_Adapters/Fixed_Tilt_Adapter.py', 'tianze_tracking': '05_Tianze_Files/Python_Adapters/Single_Axis_Adapter.py', 'RE': '06_Hao_Interface_and_Rerun/Hao_Interface.py', 'run_models': '06_Hao_Interface_and_Rerun/Rerun_Models.py'}

def load_module(name):
    path=(ROOT/MODULES[name]).resolve()
    existing=sys.modules.get(name)
    if existing is not None and Path(getattr(existing,"__file__", "")).resolve()==path:
        return existing
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    try:spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name,None)
        raise
    return module

def install():
    registry=types.ModuleType("handoff_loader")
    registry.load_module=load_module
    sys.modules["handoff_loader"]=registry
    for name in ["legacy_bridge","precipitation_adapter","crop_engine"]:
        load_module(name)
    return load_module("crop_engine")
