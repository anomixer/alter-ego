Set-Location C:\dev\alter-ego
$py = "C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
& "C:\dev\cc65\bin\ca65.exe" -t none -I src\a2 -o build\a2\p_dosload.s.o src\a2\dosload.s
& "C:\dev\cc65\bin\ca65.exe" -t none -I src\a2 -o build\a2\p_bloadtest.s.o src\a2\bloadtest.s
& "C:\dev\cc65\bin\cl65.exe" -t none -C C:\dev\pom2games\dev\cc65\apple2_hgr_c.cfg -m build\a2\bloadtest.map -o build\a2\bloadtest build\a2\p_crt0_apple2.s.o build\a2\p_dosload.s.o build\a2\p_bloadtest.s.o
& $py tools\rawbin.py build\a2\bloadtest build\a2\bloadtest.bin 0x6000
& $py C:\dev\pom2games\dev\tools\dos33.py --out build\a2\ae2_bl.dsk --bin "BLOADTST=build\a2\bloadtest.bin@0x6000" --bin "LV00=build\a2\lv00.bin@0x1000" --bas "HELLO=build\a2\hello_bl.bas"
# BSS layout: dosload owns CMD_MAX(80)+ix+hook+256 = 338 bytes, then bloadtest's
# sum_lo,sum_hi,mark_main,mark_cmd,mark_res,mark_byte0,mark_sumlo,mark_sumhi
$bss = & $py -c @"
import io,re
L=io.open('build/a2/bloadtest.map',encoding='utf-8',errors='replace').read()
m=re.search(r'__BSS_RUN__\s+([0-9A-Fa-f]{6})',L)
print(int(m.group(1),16)+338)
"@
$bss = [int]$bss
"markers at 0x$($bss.ToString('X4'))  (sum_lo sum_hi main cmd res byte0 sumlo sumhi)"
$peekarg = "peek:{0}:8" -f $bss.ToString('X4')
Set-Location C:\dev\alter-ego\tools\a2run
& .\a2run.exe --disk C:\dev\alter-ego\build\a2\ae2_bl.dsk wait:600 key:"BRUN BLOADTST`r" wait:900 pc peek:1000:8 $peekarg 2>&1
