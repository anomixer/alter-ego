"""Cross-check our generated HGR scanline table against the dev kit's table.

Reference: C:/dev/pom2games/dev/lib/hgr/hgr_scanline.inc  (hgr_lo[192], hgr_hi[192])
Ours:      build/hgr_lines.s  (hgr_line_off: 192 words)
"""
import re
import sys

KIT = r'C:\dev\pom2games\dev\lib\hgr\hgr_scanline.inc'
OURS = r'build\hgr_lines.s'


def parse_bytes(text, label):
    """Return the list of byte values emitted after a `label:` line."""
    i = text.index(label + ':')
    vals = []
    for line in text[i:].split('\n')[1:]:
        m = re.match(r'\s*\.byte\s+(.*)', line)
        if not m:
            if vals:
                break
            continue
        for tok in m.group(1).split(','):
            tok = tok.strip().replace('$', '').replace(',', '')
            if tok:
                vals.append(int(tok, 16))
    return vals


def parse_words(path):
    text = open(path, encoding='utf-8').read()
    i = text.index('hgr_line_off:')
    vals = []
    for line in text[i:].split('\n')[1:]:
        line = line.split(';')[0]
        m = re.match(r'\s*\.word\s+(.*)', line)
        if not m:
            continue
        for tok in m.group(1).split(','):
            tok = tok.strip().replace('$', '')
            if tok:
                vals.append(int(tok, 16))
    return vals


def main():
    kit = open(KIT, encoding='utf-8', errors='replace').read()
    lo = parse_bytes(kit, 'hgr_lo')
    hi = parse_bytes(kit, 'hgr_hi')
    if len(lo) != 192 or len(hi) != 192:
        raise SystemExit('unexpected kit table sizes: lo=%d hi=%d' % (len(lo), len(hi)))
    ref = [hi[y] * 256 + lo[y] for y in range(192)]

    ours = parse_words(OURS)
    if len(ours) != 192:
        raise SystemExit('our table has %d entries' % len(ours))

    bad = [(y, ref[y], ours[y]) for y in range(192) if ref[y] != ours[y]]
    print('kit  table entries: %d' % len(ref))
    print('ours table entries: %d' % len(ours))
    if bad:
        print('MISMATCHES: %d' % len(bad))
        for y, r, o in bad[:12]:
            print('  y=%-3d kit=$%04X ours=$%04X' % (y, r, o))
        raise SystemExit(1)
    print('byte-exact match on all 192 scanlines')
    print('  y=0 $%04X   y=8 $%04X   y=64 $%04X   y=191 $%04X'
          % (ref[0], ref[8], ref[64], ref[191]))
    print('  last band ends at $%04X' % (ref[191] + 40))


if __name__ == '__main__':
    sys.exit(main())
