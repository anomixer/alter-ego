"""Add an mb_present() export to src/a2/ftm.s.

mb_init already probes the Mockingboard slots and picks the VIA base
addresses, but it does not report whether anything was found.  The music
test wants to print that, so:

  * add a ZEROPAGE byte `mb_ok`
  * clear it at the top of mb_init
  * set it to 1 at @found
  * export mb_present returning 0/1

Anchors are matched with whitespace-agnostic regexes because the file is
tab-indented.
"""
import io
import re
import sys

p = r'C:\dev\alter-ego\src\a2\ftm.s'
s = io.open(p, encoding='utf-8').read()

if 'mb_present' in s:
    print('already patched')
    sys.exit(0)

def need(pat, text, label):
    m = re.search(pat, text, re.M)
    if not m:
        raise SystemExit('%s not found' % label)
    return m

# 1) export, right after the ftm_playing export
need(r'\.export\s+_ftm_playing\s*:=\s*ftm_playing', s, 'export anchor')
s = re.sub(r'(\.export\s+_ftm_playing\s*:=\s*ftm_playing)',
           r'\1\n   .export _mb_present   := mb_present', s, count=1)

# 2) zero-page byte next to via1
need(r'^(\s*)via1:\s*\.res\s*2$', s, 'zeropage anchor')
s = re.sub(r'^(\s*)via1:(\s*\.res\s*2)$',
           r'\1via1:\2\n\1mb_ok:   .res 1', s, count=1, flags=re.M)

# 3) clear at the top of mb_init
need(r'^mb_init:\s*\n\s*lda\s+#\$00\s*\n\s*sta\s+playing\s*\n', s, 'mb_init head')
s = re.sub(r'(^mb_init:\s*\n\s*lda\s+#\$00\s*\n\s*sta\s+playing\s*\n)',
           r'\1\tsta mb_ok\n', s, count=1, flags=re.M)

# 4) set at @found
need(r'^@found:\s*$', s, '@found label')
s = re.sub(r'^@found:\s*$', '@found:\n\tlda #$01\n\tsta mb_ok', s, count=1, flags=re.M)

# 5) the accessor
tail = ("\n; mb_present -> A = 1 when a Mockingboard (or clone) was found by mb_init\n"
        "mb_present:\n\tlda mb_ok\n\tldx #$00\n\trts\n")
s = s.rstrip() + '\n' + tail
io.open(p, 'w', encoding='utf-8').write(s)
print('patched ftm.s, bytes =', len(s))
