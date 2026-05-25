param(
    [string]$ZipPath
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$releaseDir = Join-Path $repoRoot "release"
$exeName = -join ([char[]](0x9AD8, 0x901F, 0x753B, 0x50CF, 0x30D3, 0x30E5, 0x30FC, 0x30A2, 0x2E, 0x65, 0x78, 0x65))
$readmeName = "README.md"
$tempBase = Join-Path ([System.IO.Path]::GetTempPath()) "FastImageViewerReleaseSmoke"
$tempRoot = $null
$exitCode = 1

function Resolve-ReleaseZip {
    param([string]$PathFromUser)

    if ($PathFromUser) {
        $resolved = [System.IO.Path]::GetFullPath($PathFromUser)
        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            throw "ERROR: zip was not found: $resolved"
        }
        return $resolved
    }

    if (-not (Test-Path -LiteralPath $releaseDir -PathType Container)) {
        throw "ERROR: release folder was not found. Run create_release_zip.bat first."
    }

    $latest = Get-ChildItem -LiteralPath $releaseDir -Filter "*.zip" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) {
        throw "ERROR: release zip was not found. Run create_release_zip.bat first."
    }

    return $latest.FullName
}

function Assert-SafeTempPath {
    param([string]$TargetPath)

    $baseFull = [System.IO.Path]::GetFullPath($tempBase)
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
    if (-not $targetFull.StartsWith($baseFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "ERROR: unsafe temp cleanup path: $targetFull"
    }
}

function Stop-ProcessesUnderPath {
    param([string]$RootPath)

    $rootFull = [System.IO.Path]::GetFullPath($RootPath)
    $targets = @(Get-Process | Where-Object {
        try {
            $_.Path -and ([System.IO.Path]::GetFullPath($_.Path)).StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)
        } catch {
            $false
        }
    })

    foreach ($target in $targets) {
        Stop-Process -Id $target.Id -Force -ErrorAction SilentlyContinue
    }
    foreach ($target in $targets) {
        Wait-Process -Id $target.Id -Timeout 5 -ErrorAction SilentlyContinue
    }
}

function Cleanup-TempRoot {
    if (-not $tempRoot -or -not (Test-Path -LiteralPath $tempRoot)) {
        return
    }

    Assert-SafeTempPath -TargetPath $tempRoot
    $lastError = $null
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        Stop-ProcessesUnderPath -RootPath $tempRoot
        try {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction Stop
            return
        } catch {
            $lastError = $_.Exception.Message
            Start-Sleep -Milliseconds 500
        }
    }

    throw "ERROR: failed to remove temp folder: $tempRoot $lastError"
}

try {
    $zipFullPath = Resolve-ReleaseZip -PathFromUser $ZipPath

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($zipFullPath)
    try {
        $entries = @($zip.Entries)
        $names = @($entries | ForEach-Object { $_.FullName.Replace('\\', '/') })
        $exeEntry = $entries | Where-Object { $_.FullName -eq $exeName } | Select-Object -First 1
        if (-not $exeEntry) {
            throw "ERROR: zip does not contain $exeName"
        }
        if ($exeEntry.Length -le 0) {
            throw "ERROR: exe in zip has zero size."
        }
        if (-not ($names -contains $readmeName)) {
            throw "ERROR: zip does not contain README.md"
        }
    } finally {
        $zip.Dispose()
    }

    New-Item -ItemType Directory -Force -Path $tempBase | Out-Null
    $tempRoot = Join-Path $tempBase ([System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    Assert-SafeTempPath -TargetPath $tempRoot

    Expand-Archive -LiteralPath $zipFullPath -DestinationPath $tempRoot -Force

    $extractedExe = Join-Path $tempRoot $exeName
    $extractedReadme = Join-Path $tempRoot $readmeName
    if (-not (Test-Path -LiteralPath $extractedExe -PathType Leaf)) {
        throw "ERROR: extracted exe was not found."
    }
    if (-not (Test-Path -LiteralPath $extractedReadme -PathType Leaf)) {
        throw "ERROR: extracted README.md was not found."
    }
    $exeInfo = Get-Item -LiteralPath $extractedExe
    if ($exeInfo.Length -le 0) {
        throw "ERROR: extracted exe size is zero."
    }

    try {
        $process = Start-Process -FilePath $extractedExe -WorkingDirectory $tempRoot -PassThru
    } catch {
        throw "ERROR: failed to start extracted exe. $($_.Exception.Message)"
    }

    Start-Sleep -Seconds 4
    $process.Refresh()
    if ($process.HasExited) {
        throw "ERROR: extracted exe exited during startup. ExitCode=$($process.ExitCode)"
    }

    $null = $process.CloseMainWindow()
    Start-Sleep -Seconds 1
    $process.Refresh()
    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        Wait-Process -Id $process.Id -Timeout 5 -ErrorAction SilentlyContinue
    }
    Stop-ProcessesUnderPath -RootPath $tempRoot

    Write-Host "RELEASE_ZIP_EXTRACT_SMOKE_OK: $zipFullPath"
    Write-Host "EXTRACTED_EXE_SIZE_BYTES: $($exeInfo.Length)"
    $exitCode = 0
} catch {
    Write-Host $_.Exception.Message
    $exitCode = 1
} finally {
    try {
        Cleanup-TempRoot
    } catch {
        Write-Host $_.Exception.Message
        $exitCode = 1
    }
}

exit $exitCode