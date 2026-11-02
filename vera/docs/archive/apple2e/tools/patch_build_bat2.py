"""Fix build/a2/build.bat: drop the doubled %% in the compiler paths and
remove the now-duplicated step-5 disk build (step 7 builds the same disk with
both binaries).
"""
import io
import re

p = r'C:\dev\alter-ego\build\a2\build.bat'
s = io.open(p, encoding='utf-8').read()

before = len(s)
s = s.replace('%CC65%%\\', '%CC65%\\')

# remove the old step 5 block (it is superseded by step 7)
old5 = re.search(r'rem 5\) bootable disk:.*?--catalog \^\s*\n\s*\|\| goto :err\s*\n\s*\n',
                 s, re.S)
if old5:
    s = s[:old5.start()] + s[old5.end():]
    print('removed the duplicated step-5 disk build')

# renumber the remaining steps so the comments read in order
s = s.replace('rem 7) bootable disk:', 'rem 5) bootable disk:')

io.open(p, 'w', encoding='utf-8').write(s)
print('build.bat fixed, bytes %d -> %d' % (before, len(s)))
for m in re.finditer(r'^rem \d+\).*$', s, re.M):
    print('  ', m.group(0))
