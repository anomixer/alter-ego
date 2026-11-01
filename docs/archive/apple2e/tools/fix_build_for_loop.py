"""Replace the invalid `for %%f ... || goto :err` block in build.bat with explicit lines.

Batch forbids `||` inside a single-line `for ... do` body ("was unexpected at this
time"), so the four -t none compiles are spelled out.  crt0_apple2.s lives in the
kit tree; hgr.s / sys.s / hgrdemo2.s live in src/a2.
"""
import io
import re

path = 'build/a2/build.bat'
src = io.open(path, encoding='utf-8').read()

start = src.index('for %%f in (crt0_apple2 hgr sys hgrdemo2)')
end = src.index('"%CC65%\\ca65.exe" -t none -I "%ROOT%\\src\\a2" -o "%B%\\p_hgr_lines.s.o"')

replacement = '\n'.join([
    '"%CC65%\\ca65.exe" -t none -I "%ROOT%\\src\\a2" -o "%B%\\p_crt0_apple2.s.o" '
    '"%KIT%\\dev\\cc65\\crt0_apple2.s" || goto :err',
    '"%CC65%\\ca65.exe" -t none -I "%ROOT%\\src\\a2" -o "%B%\\p_hgr.s.o" '
    '"%ROOT%\\src\\a2\\hgr.s" || goto :err',
    '"%CC65%\\ca65.exe" -t none -I "%ROOT%\\src\\a2" -o "%B%\\p_sys.s.o" '
    '"%ROOT%\\src\\a2\\sys.s" || goto :err',
    '"%CC65%\\ca65.exe" -t none -I "%ROOT%\\src\\a2" -o "%B%\\p_hgrdemo2.s.o" '
    '"%ROOT%\\src\\a2\\hgrdemo2.s" || goto :err',
    '',
]) + '\n'

src = src[:start] + replacement + src[end:]
io.open(path, 'w', encoding='utf-8').write(src)
print('lines =', len(src.splitlines()))
for l in src.splitlines():
    if 'p_crt0_apple2' in l or 'p_hgrdemo2' in l:
        print('  ', l.strip()[:118])
