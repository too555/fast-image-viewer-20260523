param(
    [string]$ZipPath
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$releaseDir = Join-Path $repoRoot "release"
$exeName = -join ([char[]](0x9AD8, 0x901F, 0x753B, 0x50CF, 0x30D3, 0x30E5, 0x30FC, 0x30A2, 0x2E, 0x65, 0x78, 0x65))

if (-not $ZipPath) {
    if (-not (Test-Path -LiteralPath $releaseDir -PathType Container)) {
        Write-Host "ERROR: release folder was not found. Run create_release_zip.bat first."
        exit 1
    }
    $latest = Get-ChildItem -LiteralPath $releaseDir -Filter "*.zip" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) {
        Write-Host "ERROR: release zip was not found. Run create_release_zip.bat first."
        exit 1
    }
    $ZipPath = $latest.FullName
}

$ZipPath = [System.IO.Path]::GetFullPath($ZipPath)
if (-not (Test-Path -LiteralPath $ZipPath -PathType Leaf)) {
    Write-Host "ERROR: zip was not found: $ZipPath"
    exit 1
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
try {
    $entries = @($zip.Entries)
    $names = @($entries | ForEach-Object { $_.FullName.Replace('\\', '/') })
    $errors = New-Object System.Collections.Generic.List[string]

    $exeEntry = $entries | Where-Object { $_.FullName -eq $exeName } | Select-Object -First 1
    if (-not $exeEntry) {
        $errors.Add("Missing exe: $exeName")
    } elseif ($exeEntry.Length -le 0) {
        $errors.Add("Exe size is zero: $exeName")
    }

    if (-not ($names -contains "README.md")) {
        $errors.Add("Missing README.md")
    }

    $blockedPrefixes = @("build/", "tests/", "scripts/", ".venv/", "app/", "__pycache__/", "test_artifacts/")
    $blockedExact = @("fast_image_viewer.spec", "pyproject.toml", "requirements.txt", "requirements-dev.txt", "build_exe.bat", "run_exe_smoke.bat", "create_release_zip.bat", "run_gui_smoke.bat", "start_app.bat")
    $blockedExtensions = @(".py", ".pyc", ".pyo", ".spec", ".ps1", ".bat", ".log", ".tmp")

    foreach ($name in $names) {
        $lower = $name.ToLowerInvariant()
        foreach ($prefix in $blockedPrefixes) {
            if ($lower.StartsWith($prefix)) {
                $errors.Add("Blocked folder entry: $name")
            }
        }
        foreach ($exact in $blockedExact) {
            if ($lower -eq $exact.ToLowerInvariant()) {
                $errors.Add("Blocked file entry: $name")
            }
        }
        $extension = [System.IO.Path]::GetExtension($name).ToLowerInvariant()
        if ($blockedExtensions -contains $extension) {
            $errors.Add("Blocked file type: $name")
        }
    }

    if ($errors.Count -gt 0) {
        Write-Host "ERROR: release zip check failed."
        foreach ($errorItem in $errors) {
            Write-Host " - $errorItem"
        }
        Write-Host "ZIP_CONTENTS:"
        foreach ($name in $names) {
            Write-Host " - $name"
        }
        exit 1
    }

    Write-Host "RELEASE_ZIP_CHECK_OK: $ZipPath"
    Write-Host "ZIP_CONTENTS:"
    foreach ($name in $names) {
        Write-Host " - $name"
    }
} finally {
    $zip.Dispose()
}