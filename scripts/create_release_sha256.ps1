param(
    [string]$ZipPath
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$releaseDir = Join-Path $repoRoot "release"

function Resolve-ReleaseZip {
    param([string]$PathFromUser)

    if ($PathFromUser) {
        $resolved = [System.IO.Path]::GetFullPath($PathFromUser)
        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            throw "ERROR: zip was not found: $resolved"
        }
        if ([System.IO.Path]::GetExtension($resolved).ToLowerInvariant() -ne ".zip") {
            throw "ERROR: target is not a zip file: $resolved"
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

try {
    $zipFullPath = Resolve-ReleaseZip -PathFromUser $ZipPath
    $zipInfo = Get-Item -LiteralPath $zipFullPath
    if ($zipInfo.Length -le 0) {
        throw "ERROR: zip size is zero: $zipFullPath"
    }

    $hash = Get-FileHash -LiteralPath $zipFullPath -Algorithm SHA256
    $shaPath = "$zipFullPath.sha256"
    $line = "$($hash.Hash.ToLowerInvariant())  $($zipInfo.Name)"
    [System.IO.File]::WriteAllText($shaPath, $line + [System.Environment]::NewLine, [System.Text.Encoding]::UTF8)

    $readBack = [System.IO.File]::ReadAllText($shaPath, [System.Text.Encoding]::UTF8).Trim()
    if ($readBack -ne $line) {
        throw "ERROR: failed to verify SHA256 file content."
    }

    Write-Host "SHA256_OK: $shaPath"
    Write-Host "SHA256: $($hash.Hash.ToLowerInvariant())"
    Write-Host "ZIP_FILE: $($zipInfo.Name)"
    Write-Host "ZIP_SIZE_BYTES: $($zipInfo.Length)"
    exit 0
} catch {
    Write-Host $_.Exception.Message
    exit 1
}