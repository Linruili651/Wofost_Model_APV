# Aachen Hao: final verified project, 2026-10-21

This repository was prepared from `Update/Aachen_Hao_统一运行项目`, not the older copy inside `Update/解压`.

## Latest nitrogen configuration

- Input: `04_Soil_and_Python-土壤条件与Python/Nitrogen_Inputs-氮输入/Aachen_BK50_SoilGrids_Target-目标投入估计情景.json`
- Management rules: `02_WLP_Model-WLP模型/Nitrogen_Extension-氮淋失扩展/Target_Management-目标管理.json`
- Entry: `02_WLP_Model-WLP模型/Nitrogen_Extension-氮淋失扩展/Run_Target_Inputs-计算目标补水补氮.py`
- Final rerun records and final tables: `09_Project_Records-项目记录/Final_Rerun_20261021/`

Initial mineral N is 35 kg N/ha (30 nitrate-N + 5 ammonium-N), with explicitly estimated soil parameters. These are management experiments, not field-validated Aachen predictions. The completed rerun includes 36 WOFOST7.3 PP/WLP comparisons, 18 WOFOST8.1 reference runs, and 18 water/N management cases.

`Verified_Final_Run_Inputs.json` verifies the source/input hashes against the final execution manifest. Original project status files retain their original scope and timestamps; the latest completed rerun status is `09_Project_Records-项目记录/Final_Rerun_20261021/status.json`.

## Reproduction and backup

Use Windows with Python 3.11 for crop calculations and Python 3.13 for radiation. Run `Setup_Windows_Environments-重建运行环境.ps1` to rebuild the local Python environments. Read the target-input guide before running the management experiment. The saved matched radiation/weather inputs are included, so the crop rerun can use those inputs without rerunning Radiance.

The Google Drive backup contains all selected project code, inputs, original data archive, native Radiance distribution, existing results, and final rerun records. The GitHub copy omits large archives/native programs and compressed detailed point/day outputs listed in `DRIVE_ONLY_FILES.json`. Restore those paths from the backup when exact archived outputs or the full radiation runtime are needed. Machine-specific virtual environments, caches, temporary files, and historical delivery ZIP snapshots are excluded from both copies; dependency lock files and setup scripts are retained.

## Download

- Complete portable code/input/summary package: [Aachen_Hao_Final_Run_20261021_GitHub_Ready.zip](https://drive.google.com/file/d/1lSA3ySaFGG21axucPuUCqG8iufiz4Y6y/view?usp=drivesdk)
- Full backup, including detailed outputs and original/native data: [Google Drive](https://drive.google.com/drive/folders/15SGR4OUom9ekYS6_jjnrNkMypqwb0LdM)

Download and extract the ZIP to a short directory before running. Selected source and parameter files are also expanded here for review; the ZIP contains the complete portable project layout. This archive contains 4,685 files. Its SHA-256 is `0cba86f4e18903ea3ddb2ca39e97a65ba719d07d4f0a865d5abdd97ab3b60485`.

The full Drive backup is split into 21 parts; see its START_HERE guide and merge script.

## Restore entirely from GitHub

Download this repository as ZIP and extract it, or clone it. Run `Restore_Portable_Package.ps1` to combine the 19 verified parts under `portable-package/` into the portable project ZIP. Extract that ZIP into a short directory before execution. Each part and the completed ZIP are checked with SHA-256. The Drive link above provides the same portable ZIP as a single file.
