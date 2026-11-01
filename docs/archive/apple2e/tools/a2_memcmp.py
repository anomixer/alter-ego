import struct, sys, os

B = r'C:\dev\alter-ego\build\a2'

def load_bsave(path):
    d = open(path, 'rb').read()
    if len(d) < 4:
        raise SystemExit('%s too short' % path)
    addr, ln = struct.unpack('<HH', d[:4])
    return addr, ln, d[4:]

def show(name, expect_base=None, expect=None, label=''):
    p = os.path.join(B, name)
    if not os.path.exists(p):
        print('  MISSING %s' % name); return None
    addr, ln, data = load_bsave(p)
    print('  %-22s load $%04X  len %5d  bytes %d' % (name, addr, ln, len(data)))
    if expect and expect_base is not None:
        ref = open(expect, 'rb').read()
        n = min(len(ref), len(data))
        diffs = [i for i in range(n) if ref[i] != data[i]]
        print('      vs %-18s n=%d  diffs=%d' % (os.path.basename(expect), n, len(diffs)))
        for i in diffs[:12]:
            print('        $%04X  emul=%02X  file=%02X' % (expect_base + i, data[i], ref[i]))
        if len(diffs) > 12:
            print('        ... %d more' % (len(diffs) - 12))
    return addr, ln, data

print('=== emulator memory dumps (BSAVE from AppleWin debugger) ===')
zp = show('ae2_zp.bin')
lo = show('ae2_lo.bin')
c6 = show('ae2_code6000.bin', 0x6000, os.path.join(B, 'game.bin'), 'game.bin')
c8 = show('ae2_code8800.bin')
sc = show('ae2_scr2000.bin')
lc = show('ae2_lc.bin', 0xD000, os.path.join(B, 'cold.bin'), 'cold.bin')

if c6:
    addr, ln, data = c6
    print()
    print('=== bytes at the hung PC $8874 (emulator) ===')
    off = 0x8874 - addr
    print('  emul 8860..8890:', data[off-20:off+28].hex(' '))
    ref = open(os.path.join(B, 'game.bin'), 'rb').read()
    ro = 0x8874 - 0x6000
    print('  file 8860..8890:', ref[ro-20:ro+28].hex(' '))

if lc:
    addr, ln, data = lc
    print()
    print('=== cold image in the LC bank (emulator) ===')
    print('  emul D000..D030:', data[0:0x30].hex(' '))
    ref = open(os.path.join(B, 'cold.bin'), 'rb').read()
    print('  file D000..D030:', ref[0:0x30].hex(' '))
