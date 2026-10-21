$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {throw 'Install Python 3.11 and 3.13 with the Windows py launcher first.'}
$crop = Join-Path $root '00_Runtime\Crop_Python'
$radiation = Join-Path $root '05_Tianze_Files\Radiance_Runtime\.venv'
if (-not (Test-Path -LiteralPath (Join-Path $crop 'Scripts\python.exe'))) {
    & py -3.11 -m venv $crop
    if ($LASTEXITCODE -ne 0) {throw 'Crop Python environment creation failed'}
}
$cropPython = Join-Path $crop 'Scripts\python.exe'
& $cropPython -m pip install -r (Join-Path $root '00_Runtime\requirements-crop-lock.txt')
if ($LASTEXITCODE -ne 0) {throw 'Crop dependencies failed to install'}
if (-not (Test-Path -LiteralPath (Join-Path $radiation 'Scripts\python.exe'))) {
    & py -3.13 -m venv $radiation
    if ($LASTEXITCODE -ne 0) {throw 'Radiation Python environment creation failed'}
}
$radiationPython = Join-Path $radiation 'Scripts\python.exe'
& $radiationPython -m pip install -r (Join-Path (Split-Path -Parent $radiation) 'requirements-radiation-lock.txt')
if ($LASTEXITCODE -ne 0) {throw 'Radiation dependencies failed to install'}
& $cropPython -m pip check
if ($LASTEXITCODE -ne 0) {throw 'Crop dependency check failed'}
& $radiationPython -m pip check
if ($LASTEXITCODE -ne 0) {throw 'Radiation dependency check failed'}
Write-Output 'Environments ready. Read README_Hao_Delivery.md before running.'
