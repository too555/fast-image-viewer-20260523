param(
    [string]$Destination
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$appName = -join ([char[]](0x9AD8, 0x901F, 0x753B, 0x50CF, 0x30D3, 0x30E5, 0x30FC, 0x30A2))
$exeName = "$appName.exe"
$sourceDir = Join-Path $repoRoot "dist"
$sourceExe = Join-Path $sourceDir $exeName
$sourceReadme = Join-Path $repoRoot "README.md"

if (-not $Destination) {
    $Destination = Join-Path (Join-Path $env:USERPROFILE "Apps") $appName
}
$destinationDir = [System.IO.Path]::GetFullPath($Destination)
$destinationExe = Join-Path $destinationDir $exeName
$destinationReadme = Join-Path $destinationDir "README.md"

Write-Host "LOCAL_DEPLOY_SOURCE: $sourceDir"
Write-Host "LOCAL_DEPLOY_DESTINATION: $destinationDir"

if (-not (Test-Path -LiteralPath $sourceExe -PathType Leaf)) {
    Write-Host "ERROR: source exe was not found. Run build_exe.bat first."
    Write-Host "Expected: $sourceExe"
    exit 1
}
if (-not (Test-Path -LiteralPath $sourceReadme -PathType Leaf)) {
    Write-Host "ERROR: README.md was not found: $sourceReadme"
    exit 1
}

if (-not (Test-Path -LiteralPath $destinationDir -PathType Container)) {
    New-Item -ItemType Directory -Path $destinationDir | Out-Null
    Write-Host "CREATED_DESTINATION: $destinationDir"
}

if (Test-Path -LiteralPath $destinationExe -PathType Leaf) {
    Write-Host "OVERWRITE: $destinationExe"
}
Copy-Item -LiteralPath $sourceExe -Destination $destinationExe -Force

if (Test-Path -LiteralPath $destinationReadme -PathType Leaf) {
    Write-Host "OVERWRITE: $destinationReadme"
}
Copy-Item -LiteralPath $sourceReadme -Destination $destinationReadme -Force

$exeItem = Get-Item -LiteralPath $destinationExe
$exeHash = Get-FileHash -LiteralPath $destinationExe -Algorithm SHA256

Write-Host "LOCAL_DEPLOY_OK: $destinationDir"
Write-Host "DEPLOYED_EXE: $($exeItem.FullName)"
Write-Host "DEPLOYED_EXE_SIZE_BYTES: $($exeItem.Length)"
Write-Host "DEPLOYED_EXE_SHA256: $($exeHash.Hash)"
Write-Host "DEPLOYED_README: $destinationReadme"
