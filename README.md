# Aachen APV WOFOST project

This repository contains the Aachen APV WOFOST project and records of the final run dated 2026-10-21.

## Latest nitrogen configuration

- Input: `04_Soil_and_Python/Nitrogen_Inputs/Aachen_BK50_SoilGrids_Target.json`
- Management rules: `02_WLP_Model/Nitrogen_Extension/Target_Management.json`
- Entry: `02_WLP_Model/Nitrogen_Extension/Run_Target_Inputs.py`
- Core: `06_Hao_Interface_and_Rerun/Shared_Core/Nitrogen_Engine.py`
- Final rerun evidence: `09_Project_Records/Final_Rerun_20261021/status.json`

Initial mineral nitrogen is 35 kg N/ha: 30 nitrate-N plus 5 ammonium-N. The model uses estimated soil organic matter, C:N ratios and pH. Management limits include 80 kg N/ha per application and 400 kg N/ha per season; soybean has a routine mineral-N cap of zero. These are explicitly estimated management experiments, not field-validated Aachen predictions.

The historical final rerun completed 36 WOFOST7.3 PP/WLP comparisons, 18 WOFOST8.1 technical references and 18 WOFOST8.1 management cases. Historical status, dates and execution hashes are retained as historical evidence.

## Run

Use Windows and the Python launcher with Python 3.11 for crops; Python 3.13 is also needed when recalculating radiation. See the dependency instructions below. For the management experiment, read `02_WLP_Model/Nitrogen_Extension/README_Target_Inputs.md` before running its entry point. Preserved daily radiation and weather inputs support crop reruns without recalculating Radiance. Native Radiance programs and the raw BK50 database archive are not part of this code-only distribution.

### Dependencies

After restoring and extracting the complete project, run commands from the extracted project root.

- **Crop growth and nitrogen leaching with the supplied radiation/weather inputs:** use Python 3.11 and `00_Runtime/requirements-crop-lock.txt`. Native Radiance is not required.
- **Recalculate PV shading and solar radiation:** also use Python 3.13 and `05_Tianze_Files/Radiance_Runtime/requirements-radiation-lock.txt`, and download [Radiance 6.0.2 for Windows](https://github.com/LBNL-ETA/Radiance/releases/tag/rad6R0P2) separately. Place its `bin` and `lib` folders directly under `05_Tianze_Files/Radiance_Runtime/Radiance_6.0.2/`.
- `Setup_Windows_Environments.ps1` creates both Python environments and installs their locked packages; it does **not** download or install native Radiance. For crop-only work, see the separate commands in the [dependency and Radiance setup guide](05_Tianze_Files/README_Radiance.md).

## Contents and omissions

Source code, notebooks without saved outputs, model input data, CSV result tables and final rerun records are retained. Historical thesis/Office snapshots, screenshots and pre-rendered figures are excluded; numeric source tables and plotting code remain. Summary figures are regenerated from the unchanged result tables. `OMITTED_ARTIFACTS.json` lists excluded items.

## Download the complete project

Download this repository with **Code → Download ZIP**, extract it, and run `Restore_Portable_Package.ps1`. It combines the 13 checked files under `portable-package/` into `Aachen_Hao_Project_Code_20261021.zip`. Extract that ZIP to a short directory before execution. The archive contains 4,543 files and includes all preserved CSV result data and input files. Selected source files, notebooks and parameters are also expanded in the repository for review.

Archive SHA-256: `5a7e8096dcc040e707a474ab20c30c942246856992751845f5fc5fdd88253484`. Both the individual parts and the reconstructed archive are verified automatically.
