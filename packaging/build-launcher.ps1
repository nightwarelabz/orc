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
    '/DENGINE_REL="engine\\orc.exe"',
    '/DSEED_REL="profile-seed\\user.js"',
    '/DSEED_CHROME_REL="profile-seed\\chrome\\userChrome.css"',
    '/DTRACTOR_REL="tractor\\Tractor\\Tractor.exe"'
)
$outDir = Split-Path -Parent $Out
if ($outDir -and -not (Test-Path $outDir)) { New-Item -ItemType Directory -Force $outDir | Out-Null }

$extra = @()
if ($Icon) {
    # Embed the orc face as the executable's icon (1 ICON in a .rc).
    $rc = Join-Path $env:TEMP 'orc-launcher.rc'
    $res = Join-Path $env:TEMP 'orc-launcher.res'
    Set-Content -Path $rc -Value "1 ICON `"$($Icon -replace '\\','\\')`"" -Encoding ascii
    # rc.exe must be the HOST architecture's: under an arm64 cross shell
    # the PATH rc.exe is the arm64 SDK build, which cannot start on an
    # x64 runner ("not a valid application for this OS platform", CI
    # run #1). The resource it emits is arch-neutral, so the newest
    # x64 rc.exe is always the right tool.
    $rcExe = $null
    $kits = 'C:\Program Files (x86)\Windows Kits\10\bin'
    if (Test-Path $kits) {
        $rcExe = Get-ChildItem $kits -Directory | Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName 'x64\rc.exe' } |
            Where-Object { Test-Path $_ } | Select-Object -First 1
    }
    if (-not $rcExe) { $rcExe = (Get-Command rc.exe -ErrorAction Stop).Source }
    & $rcExe /nologo /fo $res $rc
    if ($LASTEXITCODE -ne 0) { throw 'rc.exe failed' }
    $extra += $res
}

& cl.exe /nologo /O2 /W4 /utf-8 @defs /Fe:$Out "$Root\launcher\launcher.c" @extra
if ($LASTEXITCODE -ne 0) { throw 'cl.exe failed' }
Write-Host "built $Out (windows)"
