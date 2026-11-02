import sys

lc = open('build/a2/ae2_lc.bin', 'rb').read()
cold = open('build/a2/cold.bin', 'rb').read()
hgr = open('build/a2/ae2_hgr.bin', 'rb').read()

print('lc dump   %d bytes' % len(lc))
print('cold.bin  %d bytes' % len(cold))
n = min(len(lc), len(cold))
diff = [i for i in range(n) if lc[i] != cold[i]]
print('first 12 differing offsets:', ['%04X lc=%02X cold=%02X' % (i, lc[i], cold[i]) for i in diff[:12]])
print('differing bytes: %d of %d' % (len(diff), n))

# The cold stubs the game jumps into, from the generated cold_stubs.s table.
stubs = {
    'tick_frame': 0x0000, 'timer_start': 0x000B, 'timer_read': 0x0014,
    'input_poll': 0x001A, 'input_last_key': 0x008C, 'mb_init': 0x0093,
    'ftm_play': 0x0132, 'ftm_stop': 0x0194, 'ftm_tick': 0x01B7,
}
print()
print('cold stub entry bytes as seen in the LC bank (lc[$D000+off]):')
for name, off in sorted(stubs.items(), key=lambda kv: kv[1]):
    b = lc[off:off + 8]
    c = cold[off:off + 8] if off < len(cold) else b''
    print('  $%04X %-15s lc=%s  cold=%s  %s' % (
        0xD000 + off, name, b.hex(' '), c.hex(' '),
        'MATCH' if b == c else 'DIFF'))

print()
print('HGR page $2000-$203F:', hgr[:0x40].hex(' '))
uniq = sorted(set(hgr))
print('distinct byte values in the 7,680-byte HGR dump:', len(uniq), uniq[:16])
runs = {}
for v in uniq:
    runs[v] = hgr.count(v)
top = sorted(runs.items(), key=lambda kv: -kv[1])[:6]
print('most common bytes:', ['%02X x %d' % (v, c) for v, c in top])
