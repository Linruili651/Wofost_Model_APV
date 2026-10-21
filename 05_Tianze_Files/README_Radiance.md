# Dependencies and Radiance setup (Windows)

Run these commands in the root of the complete extracted project after restoring and extracting the portable package as described in the [repository README](https://github.com/Linruili651/Wofost_Model_APV#download-the-complete-project).

## Crop growth and nitrogen leaching

With the supplied radiation/weather inputs, **native Radiance is not required**. Install Python 3.11 with the Windows `py` launcher, then run:

```powershell
py -3.11 -m venv .\00_Runtime\Crop_Python
.\00_Runtime\Crop_Python\Scripts\python.exe -m pip install -r .\00_Runtime\requirements-crop-lock.txt
.\00_Runtime\Crop_Python\Scripts\python.exe -m pip check
```

Follow [README_Target_Inputs.md](../02_WLP_Model/Nitrogen_Extension/README_Target_Inputs.md) for the nitrogen management experiment.

## Recalculate PV shading and solar radiation

Also install Python 3.13 and native **Radiance 6.0.2**:

1. Download `Radiance_c1700d56_Windows.zip` from the [official Radiance 6.0.2 release](https://github.com/LBNL-ETA/Radiance/releases/tag/rad6R0P2).
2. Extract its `bin` and `lib` folders directly into `05_Tianze_Files/Radiance_Runtime/Radiance_6.0.2/`. The resulting paths must include `Radiance_6.0.2/bin/rtrace.exe`, `Radiance_6.0.2/bin/oconv.exe` and `Radiance_6.0.2/lib/`. Native binaries are not bundled with this code-only project.
3. Install the radiation Python dependencies and check the tools:

```powershell
py -3.13 -m venv .\05_Tianze_Files\Radiance_Runtime\.venv
.\05_Tianze_Files\Radiance_Runtime\.venv\Scripts\python.exe -m pip install -r .\05_Tianze_Files\Radiance_Runtime\requirements-radiation-lock.txt
.\05_Tianze_Files\Radiance_Runtime\.venv\Scripts\python.exe -m pip check
.\05_Tianze_Files\Radiance_Runtime\.venv\Scripts\python.exe .\05_Tianze_Files\Radiance_Runtime\runtime_env.py
```

The last command checks the native tools and writes `INSTALLATION_CHECK.json`. The helper sets `PATH` and `RAYPATH` for its Python process and child processes, using a temporary native-tool copy; no permanent system PATH change is needed.

## Alternative: install both Python environments

With Python 3.11 and 3.13 installed, `Setup_Windows_Environments.ps1` performs both Python environment installations above. It does **not** download or install native Radiance. Installing the Python package `bifacial_radiance` alone does not supply the project's native Radiance installation.

See the [official bifacial_radiance installation guide](https://bifacial-radiance.readthedocs.io/en/stable/user_guide/installation.html) for background. The historical native download URL and checksum are recorded in `Radiance_Runtime/DOWNLOAD_SOURCE.json` inside the complete project.
