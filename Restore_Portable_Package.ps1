$ErrorActionPreference = 'Stop'
$folder = Join-Path $PSScriptRoot 'portable-package'
$manifest = Get-Content -LiteralPath (Join-Path $folder 'Package_Parts.json') -Raw | ConvertFrom-Json
$target = Join-Path $PSScriptRoot $manifest.archive
if (Test-Path -LiteralPath $target) {
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -eq $manifest.archive_sha256) {
        Write-Output ('Package already restored and verified: ' + $target)
        exit 0
    }
    throw 'Existing ZIP checksum differs. Move it aside before retrying.'
}
foreach ($part in $manifest.parts) {
    $path = Join-Path $folder $part.name
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $part.sha256) { throw ('Part checksum mismatch: ' + $part.name) }
}
$output = [IO.File]::Open($target, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
try {
    foreach ($part in $manifest.parts) {
        $stream = [IO.File]::OpenRead((Join-Path $folder $part.name))
        try { $stream.CopyTo($output) } finally { $stream.Dispose() }
    }
} finally { $output.Dispose() }
if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $manifest.archive_sha256) { throw 'Package checksum mismatch.' }
Write-Output ('Portable project restored and verified: ' + $target)
Write-Output 'Extract the ZIP into a short path, such as D:\APV. Read README.md before running.'
