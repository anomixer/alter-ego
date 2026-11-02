"""Measure how much zero page the Apple //e build actually needs, so the
configuration can place ZEROPAGE in the region the Monitor and Applesoft leave
free (cc65's canonical apple2enh placement starts at $0080)."""
import re
import glob

rows = {}
for f in glob.glob(r'src\a2\*.s') + glob.glob(r'build\*.s'):
    seg = None
    for ln in open(f, encoding='utf-8', errors='replace').read().splitlines():
        m = re.match(r'\s*\.segment\s+"(\w+)"', ln)
        if m:
            seg = m.group(1)
            continue
        if seg not in ('ZEROPAGE', 'COLDZP'):
            continue
        m = re.match(r'\s*([A-Za-z_]\w*):\s*\.res\s+(\d+)', ln)
        if m:
            rows.setdefault(seg, []).append((m.group(1), int(m.group(2)), f))
            continue
        m = re.match(r'\s*([A-Za-z_]\w*):\s*\.byte\s+(.*)', ln)
        if m:
            n = len([x for x in m.group(2).split(',') if x.strip()])
            rows.setdefault(seg, []).append((m.group(1), n, f))

for k in sorted(rows):
    v = rows[k]
    print('%s: %d bytes' % (k, sum(x[1] for x in v)))
    for name, sz, f in v:
        print('    %-16s %3d  %s' % (name, sz, f))
