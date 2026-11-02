"""Add the music-test build steps to build/a2/build.bat.

The pipeline currently gates ftm.s with ca65 only.  musictest now links, so
build it, convert it to a DOS 3.3 BIN payload, and put it on the bootable disk
next to HGRTEST.
"""
import io
import re

p = r'C:\dev\alter-ego\build\a2\build.bat'
s = io.open(p, encoding='utf-8').read()

old = re.search(r'rem 6\) Mockingboard.*?exit /b 0', s, re.S)
if not old:
    raise SystemExit('step 6 block not found')

new = """rem 6) Mockingboard + FamiTone player: assemble gate, then the music smoke test
"%CC65%%\\ca65.exe" -t apple2enh -I "%ROOT%\\src\\a2" -o "%B%\\ftm.o" "%ROOT%\\src\\a2\\ftm.s" ^
                                                                                    || goto :err

"%CC65%%\\cl65.exe" -t apple2enh -Os -I "%ROOT%\\src" -I "%ROOT%\\src\\a2" ^
  -C "%ROOT%\\src\\a2\\a2_4000.cfg" -m "%B%\\musictest.map" -o "%B%\\musictest" ^
  "%ROOT%\\src\\a2\\ftm.s" "%ROOT%\\src\\a2\\sys.s" "%ROOT%\\src\\a2\\musictest.c" "%ROOT%\\src\\music.s" ^
                                                                                    || goto :err
"%PY%" "%ROOT%\\tools\\apple2bin.py" "%B%\\musictest" "%B%\\musictest.bin" || goto :err

rem 7) bootable disk: DOS 3.3 system tracks + HELLO launcher that BRUNs the game
echo 10 PRINT CHR$(4);"BRUN HGRTEST"> "%B%\\hello.bas"
"%PY%" "%KIT%\\dos33.py" --out "%B%\\ae2_boot.dsk" ^
  --bin "HGRTEST=%B%\\hgrtest40.bin@0x4000" --bin "MUSIC=%B%\\musictest.bin@0x4000" ^
  --bas "HELLO=%B%\\hello.bas" --catalog                                        || goto :err

echo.
echo built: %B%\\hgrtest40      (HGR engine test, BRUN at $4000)
echo        %B%\\musictest      (Mockingboard + FamiTone player, BRUN at $4000)
echo image: %B%\\ae2_boot.dsk   (bootable DOS 3.3; HELLO auto-runs BRUN HGRTEST)
echo        BRUN MUSIC on the same disk starts the music test.
echo.
echo headless check (once a2run is built in tools\\a2run):
echo   a2run --disk %B%\\ae2_boot.dsk wait:900 text
exit /b 0"""

s = s[:old.start()] + new + s[old.end():]
io.open(p, 'w', encoding='utf-8').write(s)
print('build.bat updated, bytes =', len(s))
