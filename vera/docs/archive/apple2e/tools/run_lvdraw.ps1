# 'Stop' would turn the toolchain's benign stderr warnings (cc65's "Symbol 'sp'
# is deprecated") into terminating errors, so keep going and check exit codes.
$ErrorActionPreference = 'Continue'
$root  = 'C:\dev\alter-ego'
$cc65  = 'C:\dev\cc65\bin'
$py    = 'C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$kitdev= 'C:\dev\pom2games\dev'
$b     = "$root\build\a2"
$gen   = "$root\build"
Set-Location $root

foreach ($f in @('hgr_lines.s','hgr_tiles.s','hgr_spr.s')) {
  if (-not (Test-Path "$gen\$f")) { throw "missing generated asm $gen\$f" }
}

& "$cc65\ca65.exe" -t none -I "$root\src\a2" -o "$b\p_crt0_apple2.s.o" "$kitdev\cc65\crt0_apple2.s"
& "$cc65\ca65.exe" -t none -I "$root\src\a2" -o "$b\p_sys.s.o"        "$root\src\a2\sys.s"
& "$cc65\ca65.exe" -t none -I "$root\src\a2" -o "$b\p_hgr.s.o"        "$root\src\a2\hgr.s"
& "$cc65\ca65.exe" -t none -I "$root\src\a2" -o "$b\p_lvdraw.s.o"     "$root\src\a2\lvdraw.s"
& "$cc65\ca65.exe" -t none -I "$root\src\a2" -o "$b\p_hgr_lines.s.o"  "$gen\hgr_lines.s"
& "$cc65\ca65.exe" -t none -I "$root\src\a2" -o "$b\p_hgr_tiles.s.o"  "$gen\hgr_tiles.s"
& "$cc65\cl65.exe" -t none -C "$kitdev\cc65\apple2_hgr_c.cfg" -m "$b\lvdraw.map" -o "$b\lvdraw" `
    "$b\p_crt0_apple2.s.o" "$b\p_hgr.s.o" "$b\p_sys.s.o" "$b\p_lvdraw.s.o" `
    "$b\p_hgr_lines.s.o" "$b\p_hgr_tiles.s.o"

& "$py" "$root\tools\rawbin.py" "$b\lvdraw" "$b\lvdraw.bin" 0x6000
& "$py" "$kitdev\tools\dos33.py" --out "$b\ae2_lv.dsk" `
    --bin "LVDRAW=$b\lvdraw.bin@0x6000" `
    --bin "LV00=$gen\lv\lv00.bin@0x1000" `
    --bas "HELLO=$b\hello_bl.bas"

# The marker lives at the fixed address $1FF0 (see src/a2/lvdraw.s).
$mh = '1FF0'
Write-Host "marker 0x$mh"

Set-Location "$root\tools\a2run"
& ".\a2run.exe" --disk "$b\ae2_lv.dsk" `
    wait:600 key:"BRUN LVDRAW`r" wait:2500 `
    pc "peek:1000:8" "peek:$mh`:1" "shot:$b\lv00.png" 2>&1
