# Build the Apple //e (128K) port of alter-ego and pack its DOS 3.3 disk.
#
# Layout the binaries are linked for (src/a2/a2_128.cfg, src/a2/a2_cold.cfg,
# src/a2/a2_music.cfg):
#
#   $0050-$00AF  program zero page          $00B0-$00FF  cold image zero page
#   $0400-$07FF  text page (DOS)            $0800-$0FFF  VRAM shadow (1,920 B)
#   $1000-$17FF  streaming staging page     $1800-$19FF  DOS page-zero swap
#   $2000-$3FFF  HGR page 1 (the game view)
#   $4000-$4FFF  TILES   (BLOAD'd)          $5000-$5FFF  MUSIC (BLOAD'd)
#   $6000-$95FF  program + BSS + stack      $9600-$BFFF  DOS 3.3
#   $D000-$DFFF  COLD: ftm.s + sys.s in the language-card RAM bank
#
# Nothing that can live on disk is linked into the program: the tileset, the
# music, the 26 levels and the four art screens are all BLOAD'd.  Levels load
# one at a time, on clear - the user's directive.
#
# Measured: program 12,261 B + BSS 1,050 B + stack 256 B = 13,567 of the
# 13,824-byte window below DOS.  Disk: 12,261 program + 4,096 tiles + 3,986
# music + 1,198 cold + 10,398 levels + 1,317 art.

$ErrorActionPreference = 'Continue'
$ROOT  = 'C:\dev\alter-ego'
$CC65  = 'C:\dev\cc65\bin'
$LIB   = 'C:\dev\cc65\lib\apple2enh.lib'

# lvload.s includes src/a2/tsmap.inc, the per-level track/sector map read back
# out of the packed disk.  It has to exist before the first ca65 pass, so seed a
# placeholder here; the link/pack loop below replaces it and re-links until the
# map on the disk matches the map compiled into the binary.
if (-not (Test-Path 'src\a2\tsmap.inc')) {
    Set-Content -Path 'src\a2\tsmap.inc' -Encoding ASCII -Value @(
        '; placeholder, replaced by tools/a2_tsmap.py during this build')
    foreach ($n in 0..29) { Set-Content -Append -Path 'src\a2\tsmap.inc' -Encoding ASCII -Value '  .byte $00, $00, 0, $00' }
}
$KIT   = 'C:\dev\pom2games\dev\tools'
$PY    = 'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
Set-Location $ROOT

$B   = "$ROOT\build\a2"
$GEN = "$ROOT\build"
$ART = "$GEN\art"
$LV  = "$GEN\lv"
$DSK = "$B\ae2_game.dsk"
New-Item -ItemType Directory -Force -Path $B, $ART | Out-Null

# $args is a PowerShell automatic variable, so the parameter is named $argv.
function Step($name, $exe, [string[]]$argv) {
    & $exe @argv 2>&1 | Out-String -Width 110 | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "$name failed (exit $LASTEXITCODE)" }
}

# ---------------------------------------------------------------- 1. generated
Step 'hgr_layout'  $PY @('tools\hgr_layout.py')
Step 'a2_assets'   $PY @('tools\a2_assets.py')
Step 'a2_art'      $PY @('tools\a2_art.py')

# ------------------------------------------------- 2. music image and offsets
Step 'ca65 music'  "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-I','src','-o',"$B\music_image.o",'src\a2\music_image.s')
Step 'ld65 music'  "$CC65\ld65.exe" @('-C','src\a2\a2_music.cfg','-m',"$B\music.map",'-o',"$B\music.bin","$B\music_image.o")
Write-Host ("music.bin = {0} bytes" -f (Get-Item "$B\music.bin").Length)
Step 'music offsets' $PY @('tools\a2_music_offsets.py',"$B\music.map",'src\a2\music_offsets.h')

# ---------------------------------------------- 3. cold image and jump stubs
Step 'ca65 ftm' "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-o',"$B\ftm.o",'src\a2\ftm.s')
Step 'ca65 sys' "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-o',"$B\sys.o",'src\a2\sys.s')
Step 'ca65 sfx' "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-I','src','-o',"$B\sfx_image.o",'src\a2\sfx_image.s')
Step 'ld65 cold' "$CC65\ld65.exe" @('-C','src\a2\a2_cold.cfg','-vm','-m',"$B\cold.map",'-o',"$B\cold.bin","$B\ftm.o","$B\sys.o","$B\sfx_image.o")
Write-Host ("cold.bin = {0} bytes" -f (Get-Item "$B\cold.bin").Length)
Step 'cold stubs' $PY @('tools\a2_cold_stubs.py',"$B\cold.map",'src\a2\cold_stubs.s')
Step 'ca65 stubs' "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-o',"$B\cold_stubs.o",'src\a2\cold_stubs.s')

# ------------------------------------------------------------------ 4. C code
Step 'cc65 game'  "$CC65\cc65.exe" @('-t','apple2enh','--cpu','6502','-Os','-I','src','-I','src\a2','-o',"$B\game.s",'src\game.c')
Step 'ca65 game'  "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-o',"$B\game.o","$B\game.s")
Step 'cc65 neslib' "$CC65\cc65.exe" @('-t','apple2enh','--cpu','6502','-Os','-I','src','-I','src\a2','-o',"$B\neslib.s",'src\a2\neslib.c')
Step 'ca65 neslib' "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-o',"$B\neslib.o","$B\neslib.s")

# ---------------------------------------------------------------- 5. assembly
Step 'ca65 hgr'       "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-I','src','-o',"$B\hgr.o",'src\a2\hgr.s')
Step 'ca65 spr'       "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-I','src','-o',"$B\spr.o",'src\a2\spr.s')
Step 'ca65 dosload'   "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-I','src','-o',"$B\dosload.o",'src\a2\dosload.s')
Step 'ca65 lvload'    "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-I','src','-I','src\a2','-o',"$B\lvload.o",'src\a2\lvload.s')
Step 'ca65 vram'      "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-o',"$B\vram.o",'src\a2\vram.s')
Step 'ca65 hgr_lines' "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-o',"$B\hgr_lines.o","$GEN\hgr_lines.s")
# The startup.  Linked first: it exports __STARTUP__, which keeps the library's
# crt0.o out of the image.  cc65's apple2enh crt0 does not save and restore page
# zero, does not install SOFTEV, and does not leave through DOS's warm start -
# all three are required of a DOS 3.3 BRUN'd binary.  See src/a2/crt0_dos33.s.
Step 'ca65 crt0'      "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-I','src','-I','src\a2','-o',"$B\crt0_dos33.o",'src\a2\crt0_dos33.s')

# ------------------------------------------------- 5b. patch the cc65 library
# The shipped apple2enh.lib (cc65 V2.19 - Git e11fb5c) has a defective pushax:
# it stores the low byte of the pushed value with the byte $92, which is not a
# 6502 opcode (a 1-byte JAM), so the C-stack slot's low byte is never written
# and AppleWin wedges at that address.  Measured: PC = $8B59, SP = $01FD, and no
# breakpoint at _main/_neslib_init/_lv_assets/dos_cmd_run ever fires because
# callmain() calls pushax before it calls main.  ca65 itself encodes
# sta (zp),y correctly as $91 (verified standalone), so the bad byte lives in
# the prebuilt library object.  We rebuild that one module into a private copy
# of the archive and link against the copy; the cc65 install is left untouched.
Write-Host 'patch lib: copy apple2enh.lib'
Copy-Item 'C:\dev\cc65\lib\apple2enh.lib' "$B\apple2enh_patched.lib" -Force
New-Item -ItemType Directory -Force -Path "$B\libfix" | Out-Null
Copy-Item 'src\a2\pushax_fix.s' "$B\libfix\pushax.s" -Force
Step 'ca65 pushax' "$CC65\ca65.exe" @('-t','apple2enh','--cpu','6502','-o',"$B\libfix\pushax.o","$B\libfix\pushax.s")
Step 'ar65 drop pushax' "$CC65\ar65.exe" @('d',"$B\apple2enh_patched.lib",'pushax.o')
Step 'ar65 add pushax'  "$CC65\ar65.exe" @('r',"$B\apple2enh_patched.lib","$B\libfix\pushax.o")

# ---------------------------------------------------------------- 7. launcher
# DOS 3.3 runs the program named HELLO on boot.  Applesoft hands a line that
# starts with Ctrl-D straight to the DOS command interpreter, so one line is a
# complete auto-start: the disk boots straight into the game, no typing.
# (Idiom verified in use: https://www.applefritter.com/content/execute-binary-file-boot)
# The three resident assets are loaded here, not by the game.  Measured in
# AppleWin: the in-program DOS-command emission (the kit's CR / Ctrl-D / line /
# CR through COUT after JSR $03EA) never completed - the PC ended pinned in the
# //e Monitor's COUT at $FA56 with 124 bytes of return addresses stacked, i.e.
# the CSW hook re-entered itself.  Applesoft's PRINT CHR$(4);"..." is the path
# that does work, so HELLO does the loading.  COLD lands at $2000 - the HGR page,
# which is empty at this point - because DOS cannot write the language-card RAM
# bank at BRUN time; lv_assets() moves it, and hgr_clear() fills that page right
# afterwards.  It used to stage at $1A00, which is now the RWTS track/sector
# list buffer.
$bas = "$B\hello.bas"
Set-Content -Path $bas -Encoding ASCII -Value @(
    '10 HOME',
    '20 PRINT CHR$(4);"BLOAD COLD,A$2000"',
    '30 PRINT CHR$(4);"BLOAD TILES,A$4000"',
    '40 PRINT CHR$(4);"BLOAD MUSIC,A$5000"',
    '50 PRINT CHR$(4);"BLOAD TITLEH,A$1000"',
    '60 PRINT CHR$(4);"BLOAD CREDITSH,A$1900"',
    '70 PRINT CHR$(4);"BRUN AE2GAME"',
    '80 PRINT "AE2-BACK-FROM-BRUN"',
    '90 END'
)

# ------------------------------------------------------------------ 8. pack
# --read-fast puts the T/S lists first and uses the kit's measured faster
# sector order; the files listed earliest are the ones read most often, so the
# resident assets come before the levels.
$bins = @("$KIT\dos33.py",
    "--bin", "AE2GAME=$B\game.bin@0x6000",
    "--bin", "COLD=$B\cold.bin@0xD000",
    "--bin", "TILES=$GEN\hgr_tiles.bin@0x4000",
    "--bin", "MUSIC=$B\music.bin@0x5000"
)
# a2_assets.py writes the payloads with decimal names (lv00..lv25); the disk
# name is the level number in hex because lv_load.s appends two hex digits.
foreach ($n in 0..25) {
    $bins += @("--bin", ("LV{0:X2}=$LV\lv{1:d2}.bin@0x1000" -f $n, $n))
}
# The four art screens ship in HGR-screen form (tools/a2_art.py renders them):
# CREDITSH -> $1000, TITLEH -> $1200, GAMEOVERH -> $1400, WELLDONEH -> $1600,
# matching the fixed art pointers in src/game.c.  hgr_draw_screen() paints them
# straight into the HGR page.
# TITLEH and CREDITSH are the two screens the startup path needs, and they are
# preloaded by HELLO at fixed, non-overlapping addresses: TITLEH 2,059 B at $1000
# ends $180A, CREDITSH 1,230 B at $1900 ends $1DCD.  Neither touches $2000 (the
# COLD staging page and the HGR page), and with LSTBUF moved to $1F00 they clear
# DOSBUF at $1E40 too.  GAMEOVERH and WELLDONEH are only needed at the end of a
# run, so they stay on-demand through lv_load_art().
$artLoad = @{ 'credits' = '0x1900'; 'title' = '0x1000'; 'gameover' = '0x1000'; 'welldone' = '0x1000' }
foreach ($a in 'credits','title','gameover','welldone') {
    $bins += @("--bin", ("{0}H={1}\{2}h.bin@{3}" -f $a.ToUpper(), $ART, $a, $artLoad[$a]))
}
$bins += @("--bas", "HELLO=$bas", '--catalog', '--read-fast', '--out', $DSK)

# --------------------------------------------------- 6+8. link and pack, fixed
# lvload.s embeds each level's track/sector entry point (src/a2/tsmap.inc), read
# back out of the packed image by tools/a2_tsmap.py.  Packing allocates sectors
# in file order, so the map moves whenever AE2GAME's size changes - which it
# does, because the map is inside AE2GAME.  Link, pack and re-read the map until
# the map on the disk is the map compiled into the binary.
$lvnames = @(0..25 | ForEach-Object { "LV{0:X2}" -f $_ }) + @('CREDITSH','TITLEH','GAMEOVERH','WELLDONEH')
if (-not (Test-Path 'src\a2\tsmap.inc')) {
    Set-Content -Path 'src\a2\tsmap.inc' -Encoding ASCII -Value @(
        '; placeholder, replaced by tools/a2_tsmap.py during this build')
    foreach ($n in 0..29) { Set-Content -Append -Path 'src\a2\tsmap.inc' -Encoding ASCII -Value '  .byte $00, $00, 0, $00' }
}
$stable = $false
for ($pass = 1; $pass -le 5; $pass++) {
    Write-Host "link/pack pass $pass"
    Step 'ld65 game' "$CC65\ld65.exe" @('-C','src\a2\a2_128.cfg','-m',"$B\game.map",'-o',"$B\game.bin",
        "$B\crt0_dos33.o","$B\game.o","$B\neslib.o","$B\hgr.o","$B\spr.o","$B\dosload.o","$B\lvload.o",
        "$B\vram.o","$B\hgr_lines.o","$B\cold_stubs.o","$B\apple2enh_patched.lib")
    Write-Host ("game.bin = {0} bytes (window 13,824)" -f (Get-Item "$B\game.bin").Length)

    Step 'dos33' $PY $bins
    Step 'tsmap' $PY (@('tools\a2_tsmap.py', $DSK, 'src\a2\tsmap.inc') + $lvnames)
    $new = Get-Content -Raw 'src\a2\tsmap.inc'
    if ($prev -eq $new) { $stable = $true; break }
    $prev = $new
}
if (-not $stable) { Write-Host 'TS MAP DID NOT CONVERGE'; return }

# ------------------------------------------------------------------ 9. verify
# dos33.py has no read-back mode, so the packed image is decoded from its raw
# sectors (VTOC -> catalog -> T/S lists -> data) and every file is compared
# with the binary that was packed.  A catalog line alone cannot show a broken
# T/S chain, a truncated file, or a doubled BIN header.
$vpairs = @(
    "AE2GAME=$B\game.bin", "COLD=$B\cold.bin", "TILES=$GEN\hgr_tiles.bin",
    "MUSIC=$B\music.bin"
)
foreach ($n in 0..25) { $vpairs += ("LV{0:X2}=$LV\lv{1:d2}.bin" -f $n, $n) }
foreach ($a in 'credits','title','gameover','welldone') {
    $vpairs += ("{0}H={1}\{2}h.bin" -f $a.ToUpper(), $ART, $a)
}
Step 'verify' $PY (@("tools\a2_dsk_verify.py", $DSK) + $vpairs)
if ($LASTEXITCODE -ne 0) { Write-Host "DISK VERIFY FAILED"; return }

Write-Host ""
Write-Host "disk: $DSK"
Write-Host "start it with:  BRUN AE2GAME"
