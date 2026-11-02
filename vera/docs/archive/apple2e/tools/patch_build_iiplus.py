"""Insert the II+ (-t none, kit crt0, BRUN at $6000) verification build into build.bat.

Why $6000 and not $4000: DOS 3.3 BRUN never transfers control to an image loaded at
$4000 -- the program's first instruction is never executed (PC stays in DOS).  The
same image linked and packed at $6000 runs, reaches _main, and draws.  That is the
kit's convention too (apple2_hgr_c.cfg RAM = $6000, --bin HGR=hgr.bin@0x6000).

-t none is required for a2run verification: -t apple2/-t apple2enh place the library
helper bltu2 at a hardcoded $D39A (language card), which a plain II+ core has no.
"""
import io

path = 'build/a2/build.bat'
src = io.open(path, encoding='utf-8').read()

section = r"""
rem 4b) II+ verification demo: -t none + kit crt0, BRUN at $6000.
rem     $4000 is NOT runnable under DOS 3.3 BRUN (entry never executed); $6000 is.
for %%f in (crt0_apple2 hgr sys hgrdemo2) ^
  do "%CC65%\ca65.exe" -t none -I "%ROOT%\src\a2" -o "%B%\p_%%f.s.o" "%KIT%\dev\cc65\%%f.s" 2>nul ^
  || "%CC65%\ca65.exe" -t none -I "%ROOT%\src\a2" -o "%B%\p_%%f.s.o" "%ROOT%\src\a2\%%f.s" || goto :err
"%CC65%\ca65.exe" -t none -I "%ROOT%\src\a2" -o "%B%\p_hgr_lines.s.o" "%B%\hgr_lines.s" || goto :err
"%CC65%\ca65.exe" -t none -I "%ROOT%\src\a2" -o "%B%\p_hgr_tiles.s.o" "%B%\hgr_tiles.s" || goto :err
"%CC65%\ca65.exe" -t none -I "%ROOT%\src\a2" -o "%B%\p_hgr_screen0.s.o" "%B%\hgr_screen0.s" || goto :err
"%CC65%\ca65.exe" -t none -I "%ROOT%\src\a2" -o "%B%\p_hgr_spr.s.o" "%B%\hgr_spr.s" || goto :err
"%CC65%\cl65.exe" -t none -C "%KIT%\dev\cc65\apple2_hgr_c.cfg" -m "%B%\hgrdemo6.map" -o "%B%\hgrdemo6" ^
  "%B%\p_crt0_apple2.s.o" "%B%\p_hgr.s.o" "%B%\p_sys.s.o" "%B%\p_hgrdemo2.s.o" ^
  "%B%\p_hgr_lines.s.o" "%B%\p_hgr_tiles.s.o" "%B%\p_hgr_screen0.s.o" "%B%\p_hgr_spr.s.o" || goto :err
"%PY%" "%ROOT%\tools\rawbin.py" "%B%\hgrdemo6" "%B%\hgrdemo6.bin" 0x6000 || goto :err

"""

anchor = 'rem 5) bootable disk'
assert anchor in src, 'anchor missing'
src = src.replace(anchor, section.lstrip('\n') + anchor, 1)

# Point the launcher at the demo and ship it on the disk.
src = src.replace(
    'echo 10 PRINT CHR$(4);"BRUN HGRTEST"> "%B%\\hello.bas"',
    'echo 10 PRINT CHR$(4);"BRUN HGRDEMO6"> "%B%\\hello_demo.bas"',
    1)
src = src.replace(
    '--bas "HELLO=%B%\\hello.bas" --catalog                                        || goto :err',
    '--bin "HGRDEMO6=%B%\\hgrdemo6.bin@0x6000" ^\n  --bas "HELLO=%B%\\hello_demo.bas" --catalog'
    '                                        || goto :err',
    1)

io.open(path, 'w', encoding='utf-8').write(src)
print('patched build.bat; lines =', len(src.splitlines()))
