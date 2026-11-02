"""Drop the dead sprite blitter from src/a2/hgr.s.

hgr.s ends with a second copy of the sprite routines (spr_set_buf,
spr_set_slot, spr_setup, spr_save_draw, spr_restore, spr_invert).  It exports
none of them - hgr.s .import-s the real ones from src/a2/spr.s - so the block is
pure dead weight, and it declared eleven zero-page bytes that the //e Monitor and
Applesoft need for themselves.
"""
import sys

path = r'src\a2\hgr.s'
lines = open(path, encoding='utf-8').read().splitlines(keepends=True)

start = None
for i, ln in enumerate(lines):
    if ln.startswith(';============================== sprites'):
        start = i
        break
if start is None:
    sys.exit('sprite section header not found')

note = (
    '; The sprite routines that used to follow are src/a2/spr.s\'s, and hgr.s\n'
    '; .import-s them from there: this file exported none of them, so the block\n'
    '; was dead code that also declared eleven zero-page bytes.  Zero page is the\n'
    '; binding constraint on this build - the //e Monitor owns $0050-$0051 (SPTR)\n'
    '; and $0074-$007B, Applesoft owns $0068-$0073, $00B2-$00B7, $00BE-$00BF,\n'
    '; $00C6-$00C7, $00D0-$00D3, $00E0-$00E3, $00E8-$00EB and $00F0-$00F5, and\n'
    '; DOS owns $00B8-$00C4 (the RWTS parameter block lvload.s fills in), so the\n'
    '; program\'s zero page is $0080-$00AF and every byte of it counts.\n'
)
out = lines[:start] + [note]
open(path, 'w', encoding='utf-8').write(''.join(out))
print('%s: %d lines -> %d (dropped the sprite block at line %d)'
      % (path, len(lines), len(out), start + 1))
