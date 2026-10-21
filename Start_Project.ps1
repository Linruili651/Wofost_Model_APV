$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot '00_Runtime\Crop_Python\Scripts\python.exe'
$pipelineDir = Join-Path $projectRoot '07_Full_Season_Run'
$runner = Join-Path $pipelineDir 'run_pipeline.py'
$watcher = Join-Path $pipelineDir 'watch_progress.py'
$active = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -and $_.CommandLine.Contains($runner) })
if ($active.Count -gt 0) {
    Write-Output 'The calculation is already running. No duplicate job started.'
} else {
    $lock = Join-Path $pipelineDir 'pipeline.lock'
    if (Test-Path -LiteralPath $lock) { Remove-Item -LiteralPath $lock }
    Start-Process -FilePath $python -ArgumentList @('"' + $runner + '"') -WorkingDirectory $pipelineDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $pipelineDir 'launcher_stdout.log') -RedirectStandardError (Join-Path $pipelineDir 'launcher_stderr.log')
    Write-Output 'Calculation started; completed daily checkpoints will be reused.'
}
$monitors = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -and $_.CommandLine.Contains($watcher) })
if ($monitors.Count -eq 0) {
    Start-Process -FilePath $python -ArgumentList @('"' + $watcher + '"') -WorkingDirectory $pipelineDir -WindowStyle Hidden -RedirectStandardError (Join-Path $pipelineDir 'monitor_stderr.log')
}
