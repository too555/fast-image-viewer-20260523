$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$exeName = -join ([char[]](0x9AD8, 0x901F, 0x753B, 0x50CF, 0x30D3, 0x30E5, 0x30FC, 0x30A2, 0x2E, 0x65, 0x78, 0x65))
$exePath = Join-Path (Join-Path $repoRoot "dist") $exeName

function Get-ViewerProcesses {
    Get-Process | Where-Object {
        try { $_.Path -eq $exePath } catch { $false }
    }
}

if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    Write-Host "ERROR: dist\$exeName was not found. Run build_exe.bat first."
    Write-Host "Expected path: $exePath"
    exit 1
}

$beforeIds = @(Get-ViewerProcesses | ForEach-Object { $_.Id })

try {
    $process = Start-Process -FilePath $exePath -WorkingDirectory $repoRoot -PassThru
} catch {
    Write-Host "ERROR: Failed to start exe."
    Write-Host $_.Exception.Message
    exit 1
}

Start-Sleep -Seconds 4
$process.Refresh()

if ($process.HasExited) {
    Write-Host "ERROR: exe exited during startup. ExitCode=$($process.ExitCode)"
    exit 1
}

$null = $process.CloseMainWindow()
Start-Sleep -Seconds 1
$process.Refresh()

if (-not $process.HasExited) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    Wait-Process -Id $process.Id -Timeout 5 -ErrorAction SilentlyContinue
}

$newProcesses = @(Get-ViewerProcesses | Where-Object { $beforeIds -notcontains $_.Id })
foreach ($viewerProcess in $newProcesses) {
    Stop-Process -Id $viewerProcess.Id -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1
$stillRunning = @(Get-ViewerProcesses | Where-Object { $beforeIds -notcontains $_.Id })
if ($stillRunning.Count -gt 0) {
    Write-Host "ERROR: exe started, but the smoke check could not close it. Close the app and try again."
    exit 1
}

Write-Host "EXE_SMOKE_OK: dist\$exeName exists and started successfully."
exit 0