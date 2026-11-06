# x16/tools/pack-sd.ps1 - pack the Commander X16 build for an SD card.
#
#   powershell -File x16\tools\pack-sd.ps1
#
# Reads the built files from x16\spike\dist (see x16\spike\build.ps1), adds a
# plain-text README.TXT and writes one zip whose entries sit at the archive
# root: unzipping straight into the card is the install step.
#
# Only the files the X16 build actually loads are packed.  The Apple II
# staging leftovers in dist (AE2VERA2#062000, BASIC.SYSTEM#FF0000, the PSG
# level songs, SFXBANK, ...) are deliberately left out - the X16 build has no
# ProDOS, and its music comes from the MUSIC overlay, not from .PSG files.
param(
    [string]$Dist = (Join-Path (Split-Path $PSScriptRoot -Parent) 'spike\dist'),
    [string]$Out = (Join-Path (Split-Path $PSScriptRoot -Parent) 'build\alter-ego-x16-sd.zip')
)

$ErrorActionPreference = 'Stop'

$names = @(
    'LOADER.PRG', 'GAME', 'MUSIC',
    'TILES', 'CRPAL', 'CREDITS', 'ENDPAL', 'ENDING', 'GOVER', 'GOPAL'
)
$names += 0..25 | ForEach-Object { 'LV{0:D2}' -f $_ }

# Sizes the boot chain depends on; a truncated or missing asset must fail the
# pack, not ship.
$expected = @{
    'LOADER.PRG' = 1026
    'TILES'      = 16384
    'CRPAL'      = 512
    'ENDPAL'     = 512
    'GOPAL'      = 512
    'CREDITS'    = 4096
    'ENDING'     = 4096
    'GOVER'      = 4096
}

$missing = @($names | Where-Object { -not (Test-Path (Join-Path $Dist $_)) })
if ($missing.Count) { throw "missing from $Dist : $($missing -join ', ')" }
foreach ($n in $expected.Keys | Sort-Object) {
    $len = (Get-Item (Join-Path $Dist $n)).Length
    if ($len -ne $expected[$n]) { throw "$n is $len bytes, expected $($expected[$n])" }
}

$readme = @'
        ALTER EGO  -  Commander X16 port  (2026-11-06)

This is the Apple II VERA version of Alter Ego, ported to the Commander X16.
It was built from the same C sources as the Apple II release; the new code is
the KERNAL asset loader, the boot stub and the input layer.

WHAT IS IN THIS ARCHIVE
  LOADER.PRG   the boot stub: 10 SYS 2061, then two LOADs
  GAME         the game itself (loads at $2000)
  MUSIC        the FamiTone music player overlay (loads at $1000)
  TILES        the 16 KB tile set
  CRPAL/PAL... the credits, ending and game-over screens + their palettes
  LV00..LV25   the 26 level files

HOW TO INSTALL
  Copy every file in this archive to the ROOT of the SD card (or of whatever
  directory drive 8 is on).  Keep the names as they are.

HOW TO START
  At the BASIC prompt:
     LOAD "LOADER.PRG",8,1
     RUN

  To have the machine start the game by itself, rename LOADER.PRG to
  AUTOBOOT.X16: the ROM runs a BASIC program with that name at power-on.

CONTROLS
  cursor keys ...... move, climb, jump    (or a SNES pad in port 1-4)
  X or J ........... action (A)
  Z or K ........... exchange / pick up (B)
  Enter or Space ... START (title menu, pause menu)
  1 ................ SELECT (the cow level, from the title menu)
  T ................ sound test (Escape leaves it)
  M ................ music on/off
  N ................ sound effects on/off

NOTES
  - Five levels, LEVEL CLEAR, the ending and the credits screen, exactly as on
    the Apple II and the NES.  The game is turn-based: the world moves one
    step whenever you do.
  - 512 KB of banked RAM is required (stock machines have it).
  - No DOS is needed or included: everything runs from the BASIC prompt, and
    the files must be on drive 8.  With cmdr-dos you can also COPY them into
    a directory and CD there first.
  - All checking so far was done on x16emu r49.  If anything looks wrong on
    real hardware, that is worth reporting - it would be the first report.

CREDITS
  Original game by Peter Reitan (Apple II / NES); the credits screen lists
  everyone.  Apple II VERA conversion and Commander X16 port by ANOMIXER,
  2026 - https://github.com/anomixer/alter-ego
'@ -replace "`r`n", "`n" -replace "`n", "`r`n"

$readmeBytes = [Text.Encoding]::ASCII.GetBytes($readme.TrimStart())

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$dir = Split-Path $Out -Parent
New-Item -ItemType Directory -Force -Path $dir | Out-Null
if (Test-Path $Out) { Remove-Item $Out -Force }

# Deterministic archive: entries in list order, fixed timestamps, no directory
# entries, so repacking the same dist gives the same bytes.
$stamp = [DateTimeOffset]::new([DateTime]::new(2026, 11, 6, 0, 0, 0, [DateTimeKind]::Unspecified))
$fs = [IO.File]::Create($Out)
$zip = New-Object System.IO.Compression.ZipArchive($fs, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($n in $names) {
        $bytes = [IO.File]::ReadAllBytes((Join-Path $Dist $n))
        $entry = $zip.CreateEntry($n, [System.IO.Compression.CompressionLevel]::Optimal)
        $entry.LastWriteTime = $stamp
        $s = $entry.Open()
        $s.Write($bytes, 0, $bytes.Length)
        $s.Dispose()
    }
    $entry = $zip.CreateEntry('README.TXT', [System.IO.Compression.CompressionLevel]::Optimal)
    $entry.LastWriteTime = $stamp
    $s = $entry.Open()
    $s.Write($readmeBytes, 0, $readmeBytes.Length)
    $s.Dispose()
} finally {
    $zip.Dispose()
    $fs.Dispose()
}

$outItem = Get-Item $Out
$hash = (Get-FileHash $Out -Algorithm SHA256).Hash.ToLowerInvariant()
$packed = $names + 'README.TXT'
$total = $readmeBytes.Length
foreach ($n in $names) { $total += (Get-Item (Join-Path $Dist $n)).Length }

"{0}: {1:N0} bytes, {2} entries, SHA256 {3}" -f $Out, $outItem.Length, $packed.Count, $hash
"packed payload: {0:N0} bytes (from {1})" -f $total, $Dist
$packed | ForEach-Object {
    $len = if ($_ -eq 'README.TXT') { $readmeBytes.Length } else { (Get-Item (Join-Path $Dist $_)).Length }
    "{0,-12} {1,7}" -f $_, $len
}
