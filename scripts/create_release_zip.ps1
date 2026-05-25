$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$exeName = -join ([char[]](0x9AD8, 0x901F, 0x753B, 0x50CF, 0x30D3, 0x30E5, 0x30FC, 0x30A2, 0x2E, 0x65, 0x78, 0x65))
$appName = [System.IO.Path]::GetFileNameWithoutExtension($exeName)
$distDir = Join-Path $repoRoot "dist"
$releaseDir = Join-Path $repoRoot "release"
$exePath = Join-Path $distDir $exeName
$readmePath = Join-Path $repoRoot "README.md"


function Compress-ArchiveWithRetry {
    param(
        [string[]]$SourcePaths,
        [string]$DestinationPath,
        [int]$MaxAttempts = 20
    )

    $lastError = $null
    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            Compress-Archive -LiteralPath $SourcePaths -DestinationPath $DestinationPath -Force
            return
        } catch {
            $lastError = $_.Exception.Message
            Start-Sleep -Seconds 1
        }
    }

    throw $lastError
}
function Wait-ReadableFile {
    param(
        [string]$Path,
        [int]$TimeoutSeconds = 15
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
            $stream.Dispose()
            return
        } catch {
            Start-Sleep -Milliseconds 300
        }
    }

    throw "File is not readable yet: $Path"
}
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    Write-Host "ERROR: dist\$exeName was not found. Run build_exe.bat first."
    exit 1
}

if (-not (Test-Path -LiteralPath $readmePath -PathType Leaf)) {
    Write-Host "ERROR: README.md was not found."
    exit 1
}

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

$date = Get-Date -Format "yyyyMMdd"
$zipPath = Join-Path $releaseDir ("{0}_{1}.zip" -f $appName, $date)

$items = New-Object System.Collections.Generic.List[string]
$items.Add($exePath)
$items.Add($readmePath)
foreach ($optionalName in @("LICENSE", "LICENSE.txt", "NOTICE", "NOTICE.txt")) {
    $optionalPath = Join-Path $repoRoot $optionalName
    if (Test-Path -LiteralPath $optionalPath -PathType Leaf) {
        $items.Add($optionalPath)
    }
}

try {
    Wait-ReadableFile -Path $exePath
    Compress-ArchiveWithRetry -SourcePaths $items.ToArray() -DestinationPath $zipPath
} catch {
    Write-Host "ERROR: Failed to create release zip. Close any running app window and try again."
    Write-Host $_.Exception.Message
    exit 1
}

& (Join-Path $PSScriptRoot "check_release_zip.ps1") -ZipPath $zipPath

$zipInfo = Get-Item -LiteralPath $zipPath
Write-Host "RELEASE_ZIP_OK: $($zipInfo.FullName)"
Write-Host "ZIP_SIZE_BYTES: $($zipInfo.Length)"