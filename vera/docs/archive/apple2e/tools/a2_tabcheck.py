import sys
d = open('build/a2/mem_898F_0300.bin', 'rb').read()
vals = [d[i] | (d[i + 1] << 8) for i in range(0, 384, 2)]
print('first 12 pairs:', ['%04X' % v for v in vals[:12]])
print('last 12 pairs :', ['%04X' % v for v in vals[-12:]])
lo = [v for v in vals if v < 0x2000]
print('pairs below 2000:', len(lo), 'examples:', ['%04X' % v for v in lo[:12]])
hi = sorted(set((v >> 8) & 0xFF for v in vals))
print('distinct high bytes:', ['%02X' % h for h in hi])
