# Build the orc launcher for Windows with MSVC.
#
# Usage: build-launcher.ps1 -Out build\orc.exe [-Icon branding\orc.ico]
# Run from a Visual Studio developer shell (or after vcvars64.bat) so
# cl.exe is on PATH.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Out,
    [string]$Icon
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

$defs = @(
    '/DENGINE_REL="engine\\librewolf.exe"',
    '/DSEED_REL="profile-seed\\user.js"'
)
$outDir = Split-Path -Parent $Out
if ($outDir -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Force $outDir | Out-Null }

$extra = @()
if ($Icon) {
    # Embed the orc face as the executable's icon (1 ICON in a .rc).
    $rc = Join-Path $env:TEMP 'orc-launcher.rc'
    $res = Join-Path $env:TEMP 'orc-launcher.res'
    Set-Content -Path $rc -Value "1 ICON `"$($Icon -replace '\\','\\')`"" -Encoding ascii
    & rc.exe /nologo /fo $res $rc
    if ($LASTEXITCODE -ne 0) { throw 'rc.exe failed' }
    $extra += $res
}

& cl.exe /nologo /O2 /W4 /utf-8 @defs /Fe:$Out "$Root\launcher\launcher.c" @extra
if ($LASTEXITCODE -ne 0) { throw 'cl.exe failed' }
Write-Host "built $Out (windows)"
