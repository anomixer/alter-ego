# Build the CX16 bring-up probe with cc65's cx16 target.
#   powershell -File x16\probe\build.ps1
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:CC65_BIN = if ($env:CC65_BIN) { $env:CC65_BIN } else { 'C:\dev\cc65\bin' }

& "$env:CC65_BIN\cl65.exe" -t cx16 -O -o "$here\vera_probe.prg" "$here\main.c"
if ($LASTEXITCODE -ne 0) { throw "cl65 failed ($LASTEXITCODE)" }
Get-Item "$here\vera_probe.prg" | Select-Object Name, Length
