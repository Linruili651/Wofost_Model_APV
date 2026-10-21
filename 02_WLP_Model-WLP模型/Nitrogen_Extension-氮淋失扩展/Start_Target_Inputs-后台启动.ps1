param([int]$Workers = 2)
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$pythonPath = Join-Path $projectRoot '00_Runtime-运行环境\Crop_Python\Scripts\python.exe'
$scriptPath = Join-Path $PSScriptRoot 'Run_Target_Inputs-计算目标补水补氮.py'
$existing = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -and $_.CommandLine.Contains('Run_Target_Inputs-计算目标补水补氮.py') }
if ($existing) { Write-Output "Existing target-input process: $($existing.ProcessId -join ', ')"; exit 0 }
$settingsPath = Join-Path $projectRoot '06_Hao_Interface_and_Rerun-Hao接口与复跑\Shared_Core-共享核心\Runtime_Cache-运行缓存\.pcse\user_settings.py'
$settingsFolder = Split-Path -Parent $settingsPath
New-Item -ItemType Directory -Path $settingsFolder -Force | Out-Null
$loggingBlock = [System.IO.File]::ReadAllText((Join-Path $PSScriptRoot 'PCSE_Process_Logging-进程独立日志.py'))
$settingsText = if (Test-Path -LiteralPath $settingsPath) { [System.IO.File]::ReadAllText($settingsPath) } else { '' }
if ($settingsText.Contains('# BEGIN TARGET INPUT PROCESS LOGGING')) {
    $settingsText = [regex]::Replace($settingsText, '(?s)# BEGIN TARGET INPUT PROCESS LOGGING.*?# END TARGET INPUT PROCESS LOGGING', $loggingBlock)
} else { $settingsText += "`n" + $loggingBlock + "`n" }
[System.IO.File]::WriteAllText($settingsPath, $settingsText, [System.Text.UTF8Encoding]::new($false))
$outputPath = Join-Path $projectRoot '07_Full_Season_Run-完整季运行\target_resource_run'
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
$process = Start-Process -FilePath $pythonPath -ArgumentList @('-u', ('"' + $scriptPath + '"'), '--workers', $Workers) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $outputPath 'run.log') -RedirectStandardError (Join-Path $outputPath 'error.log')
Write-Output "Started target-input simulation. PID: $($process.Id)"
