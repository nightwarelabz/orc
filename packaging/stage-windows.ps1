# Stage the Windows orc package.
#
# Downloads the pinned LibreWolf portable zip for the requested arch,
# verifies it twice (sha256 pinned in installers/engine-manifest.json
# AND the official .sha256sum sidecar at dl.librewolf.net), then lays
# out a portable orc/ tree and zips it.
#
# Usage:
#   stage-windows.ps1 -Arch x86_64 -Version 0.1.0 -OrcExe build\orc.exe [-OutDir dist]
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet('x86_64', 'arm64')][string]$Arch,
    [Parameter(Mandatory = $true)][string]$Version,
    [Parameter(Mandatory = $true)][string]$OrcExe,
    [string]$OutDir = 'dist'
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path $OrcExe)) { throw "launcher not found: $OrcExe (build it first with packaging/build-launcher.ps1)" }

$manifest = Get-Content (Join-Path $Root 'installers\engine-manifest.json') -Raw | ConvertFrom-Json
$key = "windows-$Arch"
$artifact = $manifest.artifacts.$key
if (-not $artifact) { throw "manifest has no artifact for $key" }
$engineVersion = $manifest.engineVersion
$base = "https://dl.librewolf.net/librewolf/$engineVersion"

$work = Join-Path $env:TEMP "orc-stage-windows-$Arch"
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Force $work | Out-Null

$zipPath = Join-Path $work $artifact.file
Write-Host "downloading $($artifact.file)"
Invoke-WebRequest -Uri "$base/$($artifact.file)" -OutFile $zipPath
Invoke-WebRequest -Uri "$base/$($artifact.file).sha256sum" -OutFile "$zipPath.sha256sum"

# Verify twice. Any mismatch stops the build.
$actual = (Get-FileHash -Algorithm SHA256 $zipPath).Hash.ToLowerInvariant()
$sidecar = ((Get-Content "$zipPath.sha256sum" -Raw) -split '\s+')[0].ToLowerInvariant()
if ($actual -ne $artifact.sha256.ToLowerInvariant()) {
    throw "sha256 mismatch vs manifest for $($artifact.file): got $actual"
}
if ($actual -ne $sidecar) {
    throw "sha256 mismatch vs official sidecar for $($artifact.file): got $actual, sidecar $sidecar"
}
Write-Host "verified sha256 $actual"

# Extract and find the engine.
$extract = Join-Path $work 'extract'
Expand-Archive -Path $zipPath -DestinationPath $extract -Force
$exe = Get-ChildItem -Path $extract -Filter 'librewolf.exe' -Recurse -File | Select-Object -First 1
if (-not $exe) { throw 'librewolf.exe not found in the portable zip' }
$engineDir = $exe.Directory.FullName
Write-Host "engine at $engineDir"

# Stage: <OutDir>/stage-windows-<arch>/orc/
$stageRoot = Join-Path $OutDir "stage-windows-$Arch"
$stage = Join-Path $stageRoot 'orc'
if (Test-Path $stageRoot) { Remove-Item -Recurse -Force $stageRoot }
New-Item -ItemType Directory -Force $stage | Out-Null

Copy-Item $OrcExe (Join-Path $stage 'orc.exe')
Copy-Item (Join-Path $Root 'branding\orc.ico') (Join-Path $stage 'orc.ico')
Copy-Item -Recurse $engineDir (Join-Path $stage 'engine')
# orc's policy layer lives inside the engine root as distribution/.
Copy-Item -Recurse (Join-Path $Root 'distribution') (Join-Path $stage 'engine\distribution')
# First-run profile seed.
New-Item -ItemType Directory -Force (Join-Path $stage 'profile-seed') | Out-Null
Copy-Item (Join-Path $Root 'profile\user.js') (Join-Path $stage 'profile-seed\user.js')

# Portable zip + checksum.
New-Item -ItemType Directory -Force $OutDir | Out-Null
$outZip = Join-Path $OutDir "orc-$Version-windows-$Arch.zip"
if (Test-Path $outZip) { Remove-Item -Force $outZip }
Compress-Archive -Path $stage -DestinationPath $outZip -CompressionLevel Optimal
$hash = (Get-FileHash -Algorithm SHA256 $outZip).Hash.ToLowerInvariant()
"$hash  $(Split-Path -Leaf $outZip)" | Set-Content "$outZip.sha256sum" -Encoding ascii
Write-Host "staged $stage"
Write-Host "packed  $outZip  sha256 $hash"
