# Build the ALTER EGO CX16 spike: real a2vera game sources with the cc65 cx16
# target, plus the X16-specific boot chain and asset layer.
#   powershell -File x16\spike\build.ps1
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$cc = if ($env:CC65_BIN) { $env:CC65_BIN } else { 'C:\dev\cc65\bin' }
$src = Join-Path $root 'vera\src\a2vera'
$gen = Join-Path $root 'vera\build'
$work = Join-Path $PSScriptRoot 'work'
$dist = Join-Path $PSScriptRoot 'dist'
$lib = Join-Path (Split-Path $cc -Parent) 'lib\cx16.lib'
New-Item -ItemType Directory -Force -Path $work, $dist | Out-Null

function Run([string]$exe, [string[]]$argv) {
    & (Join-Path $cc $exe) @argv
    if ($LASTEXITCODE -ne 0) { throw "$exe failed ($LASTEXITCODE): $($argv -join ' ')" }
}

# Generated FamiTone data from the existing a2vera build (same 6502 encoding).
Copy-Item (Join-Path $gen 'ftm_tables.h'), (Join-Path $gen 'ftm_sfx_layout.inc') $work -Force
Copy-Item (Join-Path $gen 'fami_modules_ftm.o'), (Join-Path $gen 'ftm_sfx_data.o'), `
          (Join-Path $gen 'ftm_pitch_table.o'), (Join-Path $gen 'ftm_envelopes.o') $work -Force

$srcIncs = @('-I', $src, '-I', (Join-Path $root 'vera\src'))
$common = @('-t', 'cx16', '-DVERA_BASE=0x9F20', '-DFTM_VERA=1', '-DVERA_X16=1')
# Optional test build: -DAE_X16_AUTOSTART=<level> skips the title menu so an
# automated capture can reach gameplay (x16emu cannot be driven by SendKeys).
if ($env:AE_X16_AUTOSTART) { $common += "-DAE_X16_AUTOSTART=$($env:AE_X16_AUTOSTART)" }
# Optional beacons on $9FB9 (x16emu "User debug 1") for tracing asset loads.
if ($env:AE_DEBUG) { $common += '-DAE_DEBUG' }
# Optional music tempo trim in 1/256 of a FamiTone tick per frame (0 = exact
# NES 60 Hz, 8 = about +3%).  The overlay is built with the same flags.
if ($env:AE_X16_TEMPO_TRIM) { $common += "-DAE_X16_TEMPO_TRIM=$($env:AE_X16_TEMPO_TRIM)" }
# Extra -D flags for one-off porting instrumentation, space separated
# (e.g. AE_EXTRA_DEFINES='AE_DEBUG_XY' enables the $9FB9 position beacon).
if ($env:AE_EXTRA_DEFINES) {
    foreach ($d in $env:AE_EXTRA_DEFINES.Split(' ', [StringSplitOptions]::RemoveEmptyEntries)) {
        $common += "-D$d"
    }
}

# --- X16 platform layer ---------------------------------------------------
Run 'cc65.exe' (@($common + @('-O', '-Cl')) + $srcIncs + @('-o', (Join-Path $work 'asset_cx16.s'), (Join-Path $PSScriptRoot 'asset_cx16.c')))
Run 'ca65.exe' @('--cpu', '65C02', '-o', (Join-Path $work 'asset_cx16.o'), (Join-Path $work 'asset_cx16.s'))
Run 'cc65.exe' (@($common + @('-O')) + $srcIncs + @('-o', (Join-Path $work 'io_cx16.s'), (Join-Path $PSScriptRoot 'io_cx16.c')))
Run 'ca65.exe' @('--cpu', '65C02', '-o', (Join-Path $work 'io_cx16.o'), (Join-Path $work 'io_cx16.s'))
Run 'ca65.exe' @('--cpu', '65C02', '-o', (Join-Path $work 'kload_cx16.o'), (Join-Path $PSScriptRoot 'kload_cx16.s'))
Run 'ca65.exe' @('--cpu', '65C02', '-o', (Join-Path $work 'clrchn_cx16.o'), (Join-Path $PSScriptRoot 'clrchn_cx16.s'))

# --- main game binary -----------------------------------------------------
Run 'cc65.exe' (@($common + @('-g', '-Os', '-Cl')) + $srcIncs + @('-o', (Join-Path $work 'main.s'), (Join-Path $src 'main.c')))
Run 'ca65.exe' @('--cpu', '65C02', (Join-Path $work 'main.s'), '-o', (Join-Path $work 'main.o'))
Run 'cc65.exe' (@($common + @('-Oirs', '-Cl')) + $srcIncs + @('-o', (Join-Path $work 'oam.s'), (Join-Path $src 'oam.c')))
Run 'ca65.exe' @('--cpu', '65C02', (Join-Path $work 'oam.s'), '-o', (Join-Path $work 'oam.o'))
Run 'ca65.exe' @('--cpu', '65C02', '-D', 'VERA_BASE=$9F20', '-D', 'FTM_VERA=1', '-D', 'VERA_X16=1', '-I', $src, '-I', (Join-Path $root 'vera\src'), '-o', (Join-Path $work 'title.o'), (Join-Path $src 'title.s'))
Run 'ca65.exe' @('--cpu', '65C02', '-D', 'VERA_BASE=$9F20', '-D', 'FTM_VERA=1', '-o', (Join-Path $work 'oam_core.o'), (Join-Path $src 'oam.s'))
Run 'ca65.exe' @('--cpu', '65C02', '-o', (Join-Path $work 'music_imports.o'), (Join-Path $src 'music_imports_ftm.s'))
Run 'ca65.exe' @('--cpu', '65C02', '-D', 'VERA_BASE=$9F20', '-D', 'FTM_VERA=1', '-I', $work, '-o', (Join-Path $work 'ftm_sfx_simple.o'), (Join-Path $src 'ftm_sfx_simple.s'))
Run 'ca65.exe' @('--cpu', '65C02', '-o', (Join-Path $work 'input.o'), (Join-Path $PSScriptRoot 'input_cx16.s'))
# Extra game code that lives in the free hole at $92DC ($92DB FTMTABLE end,
# $93A0 FTM_HIGH_BSS start); see gate_cx16.s and game.cfg.
Run 'ca65.exe' @('--cpu', '65C02', '-o', (Join-Path $work 'gate.o'), (Join-Path $PSScriptRoot 'gate_cx16.s'))
Run 'ca65.exe' @('--cpu', '65C02', '-o', (Join-Path $work 'loadaddr.o'), (Join-Path $PSScriptRoot 'loadaddr.s'))
Run 'ca65.exe' @('--cpu', '65C02', '-D', 'MUSIC_OVERLAY=1', '-o', (Join-Path $work 'music_loadaddr.o'), (Join-Path $PSScriptRoot 'loadaddr.s'))

Run 'ld65.exe' @('-C', (Join-Path $PSScriptRoot 'game.cfg'), '-m', (Join-Path $work 'game.map'), '-o', (Join-Path $dist 'GAME'), `
    (Join-Path $work 'title.o'), (Join-Path $work 'main.o'), (Join-Path $work 'oam.o'), (Join-Path $work 'oam_core.o'), `
    (Join-Path $work 'input.o'), (Join-Path $work 'music_imports.o'), (Join-Path $work 'fami_modules_ftm.o'), `
    (Join-Path $work 'ftm_pitch_table.o'), (Join-Path $work 'ftm_sfx_simple.o'), (Join-Path $work 'loadaddr.o'), `
    (Join-Path $work 'io_cx16.o'), (Join-Path $work 'asset_cx16.o'), (Join-Path $work 'kload_cx16.o'), `
    (Join-Path $work 'clrchn_cx16.o'), (Join-Path $work 'gate.o'), $lib)

# --- music overlay --------------------------------------------------------
Run 'cc65.exe' (@($common + @('-Os', '-Cl')) + @('-I', $work) + @('-o', (Join-Path $work 'ftm_player.s'), (Join-Path $src 'ftm_player.c')))
Run 'ca65.exe' @('--cpu', '65C02', '-o', (Join-Path $work 'ftm_player.o'), (Join-Path $work 'ftm_player.s'))
Run 'ca65.exe' @('--cpu', '65C02', '-o', (Join-Path $work 'music_api.o'), (Join-Path $src 'music_api_ftm.s'))
Run 'ld65.exe' @('-C', (Join-Path $PSScriptRoot 'music.cfg'), '-m', (Join-Path $work 'music.map'), '-o', (Join-Path $dist 'MUSIC'), `
    (Join-Path $work 'music_api.o'), (Join-Path $work 'ftm_player.o'), (Join-Path $work 'ftm_envelopes.o'), `
    (Join-Path $work 'ftm_sfx_data.o'), (Join-Path $work 'music_loadaddr.o'), $lib)

# --- boot chain -----------------------------------------------------------
Run 'cl65.exe' @('-t', 'cx16', '-C', (Join-Path $PSScriptRoot 'loader.cfg'), '-o', (Join-Path $dist 'LOADER.PRG'), (Join-Path $PSScriptRoot 'loader.s'))

# --- runtime files --------------------------------------------------------
Copy-Item (Join-Path $gen 'stage\*') $dist -Force
$tiles = [System.IO.File]::ReadAllBytes((Join-Path $gen 'stage\TILES'))
if ($tiles.Length -ne 16384) { throw "TILES is $($tiles.Length) bytes, expected 16384" }

# --- credits screen wording -----------------------------------------------
# a2vera_art.py bakes the platform line into the CREDITS nametable.  Regenerate
# only that asset with the X16 wording, into work\art, so vera\build (and the
# Apple II release artifacts) stay byte-identical, then overwrite the copies.
$artOut = Join-Path $work 'art'
$py = if ($env:PYTHON) { $env:PYTHON } else { 'python' }
try {
    $env:AE2VERA_CREDITS_PLATFORM = 'COMMANDER X16'
    $env:AE2VERA_ART_OUT = $artOut
    & $py (Join-Path $root 'vera\tools\a2vera_art.py') 'credits'
    if ($LASTEXITCODE -ne 0) { throw "a2vera_art.py exited $LASTEXITCODE" }
    Copy-Item (Join-Path $artOut 'credits_map.bin') (Join-Path $dist 'CREDITS') -Force
    Copy-Item (Join-Path $artOut 'credits_palette.bin') (Join-Path $dist 'CRPAL') -Force
} catch {
    # Keep building with the Apple II wording rather than failing the port build;
    # set PYTHON=<path> if python is not on PATH.
    Write-Warning "credits line not regenerated ($($_.Exception.Message)); dist keeps 'APPLE II VERA CONVERSION BY'"
} finally {
    $env:AE2VERA_CREDITS_PLATFORM = ''
    $env:AE2VERA_ART_OUT = ''
}

Get-ChildItem $dist | Select-Object Name, Length | Format-Table -AutoSize
