param(
    [ValidateSet('check','smoke')][string]$Action = 'check',
    [ValidateSet('fixed_tilt','vertical_pv','single_axis','all')][string]$Model = 'fixed_tilt'
)
$ErrorActionPreference = 'Stop'
$runtimeFolder = @(Get-ChildItem -LiteralPath $PSScriptRoot -Directory -Filter 'Radiance_Runtime-*')
if ($runtimeFolder.Count -ne 1) { throw 'Expected one Radiance_Runtime folder next to this launcher.' }
$pythonPath = Join-Path $runtimeFolder[0].FullName '.venv\Scripts\python.exe'
$launcherPath = Join-Path $runtimeFolder[0].FullName 'launch_aachen.py'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Local radiation Python environment is missing. Follow README_Radiance.md to recreate it.'
}
$env:PYTHONIOENCODING = 'utf-8'
& $pythonPath $launcherPath --action $Action --model $Model
exit $LASTEXITCODE
