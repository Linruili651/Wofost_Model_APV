- `Radiance_Runtime/Radiance_c1700d56_Windows.zip`:  LBNL  GitHub release  Windows ,  33.6 MB.
- `Radiance_Runtime/Radiance_6.0.2/`: Extracted `bin`  `lib` .
- `Radiance_Runtime/.venv/`:  Python , .
- `Radiance_Runtime/DOWNLOAD_SOURCE.json`: , , , SHA-256 .
- `Radiance_Runtime/INSTALLATION_CHECK.json`:  Python, .
- `Radiance_Runtime/AACHEN_SMOKE_CHECK.json`: .




```powershell
.\Start_Tianze_Aachen.ps1
```


```powershell
.\Start_Tianze_Aachen.ps1 -Action smoke -Model fixed_tilt
```





```python
from pathlib import Path
import sys
runtime = Path(r" Radiance_Runtime ")
sys.path.insert(0, str(runtime))
from runtime_env import configure
configure()
```


Windows ; Python .  Python 3.13,  `Radiance_Runtime` :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-radiation-lock.txt
```



- Radiance : https://www.radiance-online.org/about
- Tianze : https://bifacial-radiance.readthedocs.io/en/stable/user_guide/installation.html
- : https://github.com/LBNL-ETA/Radiance/releases/tag/rad6R0P2
