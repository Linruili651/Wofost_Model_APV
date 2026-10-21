# Aachen APV WOFOST project — English edition

This is the English-only edition of the verified final project dated 2026-10-21. Folder names, file names, code references, comments, labels, and documentation use English. The original working project remains unchanged locally.

## Latest nitrogen configuration

- Input: `04_Soil_and_Python/Nitrogen_Inputs/Aachen_BK50_SoilGrids_Target.json`
- Management rules: `02_WLP_Model/Nitrogen_Extension/Target_Management.json`
- Entry: `02_WLP_Model/Nitrogen_Extension/Run_Target_Inputs.py`
- Core: `06_Hao_Interface_and_Rerun/Shared_Core/Nitrogen_Engine.py`
- Final rerun evidence: `09_Project_Records/Final_Rerun_20261021/status.json`

Initial mineral nitrogen is 35 kg N/ha: 30 nitrate-N plus 5 ammonium-N. The model uses estimated soil organic matter, C:N ratios and pH. Management limits include 80 kg N/ha per application and 400 kg N/ha per season; soybean has a routine mineral-N cap of zero. These are explicitly estimated management experiments, not field-validated Aachen predictions.

The historical final rerun completed 36 WOFOST7.3 PP/WLP comparisons, 18 WOFOST8.1 technical references and 18 WOFOST8.1 management cases. Historical status, dates and execution hashes are retained as historical evidence. Translation is not a claim of a new calibrated experiment.

## Run

Use Windows and the Python launcher with Python 3.11 for crops and Python 3.13 for radiation. Run `Setup_Windows_Environments.ps1` to rebuild dependencies. For the management experiment, read `02_WLP_Model/Nitrogen_Extension/README_Target_Inputs.md` before running its entry point. Preserved daily radiation and weather inputs support crop reruns without recalculating Radiance. Native Radiance programs and the raw BK50 database archive are not part of this code-only distribution.

`TRANSLATION_VERIFICATION.json` records syntax, numeric-table and algorithm checks. `ENGLISH_RELEASE_MANIFEST.json` supplies release-file SHA-256 checksums. Updated checkpoint manifests explicitly identify their translation rebase and retain the original execution identity. Source-copy manifests retain original provenance hashes when their presentation copy changed.

## Contents and omissions

Source code, notebooks without saved outputs, model input data, CSV result tables and final rerun records are retained. Historical thesis/Office snapshots, screenshots and pre-rendered figures were removed to avoid embedded Chinese text; numeric source tables and plotting code remain. English summary figures are regenerated from the unchanged result tables. `OMITTED_ARTIFACTS.json` lists excluded items under English names.

Google Drive was not updated, as requested. This English edition is published only to GitHub. Earlier Git commits preserve the previous bilingual delivery; the current branch and portable archive are the English edition.
