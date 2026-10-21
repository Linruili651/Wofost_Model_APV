"""Run the six-crop WLP_MLWB entry. / WLP_MLWB. """

# Load bilingual file paths through stable internal Python module names.
from pathlib import Path as _Path
import runpy as _runpy
_package_root = next(p for p in _Path(__file__).resolve().parents if (p / '06_Hao_Interface_and_Rerun').is_dir())
_registry = _runpy.run_path(str(_package_root / '06_Hao_Interface_and_Rerun/Shared_Core/Module_Loader.py'))
_registry["install"]()

import sys
if __name__=="__main__":
    sys.argv[1:1]=["--mode",'WLP_MLWB']
    _registry["load_module"]("run_models").main()
