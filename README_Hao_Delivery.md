# Hao delivery

Use this extracted folder as one project. Do not combine its code with another 19/20 version. The ZIP is a delivery container; execution reads the extracted files.

## Scope

Six crops: winter wheat, spring barley, grain maize, potato, sugar beet and soybean. Current long-run comparison: open field, fixed-tilt conventional opaque PV, and fixed-tilt semi-transparent PV; two modes, WOFOST7.3 PP and layered WLP. This gives 36 aggregate comparisons, 12 crop-specific two-panel figures, and one cross-crop relative-yield/ET summary normalised to each crop/mode open-field baseline. Tracking and vertical PV are outside the current full-season study. Their original programs are preserved for reference.

Read DELIVERY_STATUS.json first. `interim_full_season_running` means the ZIP contains a running snapshot, not completed final figures. The same delivery ZIP will be rebuilt when the full pipeline finishes.

## Reproduce

The verified complete-season launcher targets Windows, Python 3.11 for crops and Python 3.13 for radiation. Machine-bound virtual environments are omitted from the ZIP. Install both Python versions with the Windows `py` launcher, then run Setup_Windows_Environments.ps1. It creates both environments within this project and installs recorded dependencies. Native Radiance binaries are not included. Download Radiance 6.0.2 separately when recalculating radiation; see [the dependency guide](05_Tianze_Files/README_Radiance.md). Crop and nitrogen runs using the supplied radiation inputs do not require native Radiance.

Run Start_Project.ps1 to start/resume. Open 08_Thesis_Results/View_Progress.html after the monitor starts. Inputs are under 03–06; the queue and checkpoints are under 07; collected tables/figures are under 08. Completed radiation days are reused; incomplete days are recomputed.

A restored original-data snapshot preserves all members of the requested old ZIP outside the current delivery archive. Old-only files included in 11_Original_Package_Compatibility are inactive historical references. Do not use their entry points.

## Nitrogen

New adaptive-input experiment

The project includes WOFOST8.1/SNOMIN, crop parameters, nitrogen-source records, reference runs and strict field-input checks. Aachen field nitrogen runs remain blocked by missing sourced soil-N, soil chemistry and management inputs. Published technical controls are explicitly labelled and must not be interpreted as field-calibrated Aachen results. PP/WLP73 outputs do not calculate nitrogen leaching.

Do not compare a WOFOST7.3 WLP yield with WOFOST8.1 NWLP and attribute the entire difference to nitrogen. Matched PP81/WLP81 reference entries are provided for version-consistent comparisons.

## Interpretation

Weather is a matched PVGIS synthetic TMY, not an observed experiment year. Radiation uses Tianze's complete hourly algorithm with its original low accuracy and a common 15×15 ground grid; numerical convergence has not been demonstrated. Crop/soil/optical assumptions are uncalibrated. Yield is harvest-organ dry matter; ET is transpiration plus soil evaporation, not irrigation requirement. Rain redistribution and APV microclimate feedbacks are not modelled.

See 09_Project_Records/Delivery_Comparison.md for changes against the requested old package and Delivery_Input_Checksums.json for portable input/code checksums.
