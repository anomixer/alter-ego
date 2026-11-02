#!/usr/bin/env python3
"""Parse a real Apple II DOS 3.3 .dsk image: VTOC + catalog.

Used to verify the DOS 3.3 layout empirically against a known-good image
(C:\\dev\\a2vera\\a2vera_dos33.dsk) before writing our own packager.
"""
import sys

SEC = 256
TRKS = 35
SECS = 16


def read_sector(data, trk, sec):
    off = (trk * SECS + sec) * SEC
    return data[off:off + SEC]


def main(path):
    data = open(path, 'rb').read()
    print('image bytes =', len(data), '(35*16*256 =', TRKS * SECS * SEC, ')')
    print('prodos?', data[0:4] == b'PA', '  2MG?', data[:4] == b'2MG\x00')

    v = read_sector(data, 17, 0)
    print('\n=== VTOC (T17,S0) ===')
    print('  VTOC link  T%d S%d  (expect T17 S0)  raw=%02X %02X' % (v[1], v[2], v[1], v[2]))
    print('  bit map    T%d S%d (expect T17 S11)  raw=%02X %02X' % (v[3], v[4], v[3], v[4]))
    print('  format byte      = %02X' % v[5])
    print('  max sector/track = %d (%02X)' % (v[6], v[6]))
    print('  tracks           = %d (%02X)' % (v[7], v[7]))
    print('  sectors/track    = %d (%02X)' % (v[8], v[8]))
    print('  reserved         = %d' % v[10])
    print('  file type        = %02X' % v[11])
    print('  aux (load addr)  = %02X %02X -> $%02X%02X' % (v[12], v[13], v[13], v[12]))
    print('  sectors used     = %d (%02X %02X)' % (v[14] + v[15] * 256, v[15], v[14]))
    print('  bitmap bytes 11..102 (free=bit set):')
    bm = v[11 + 1:103]
    free = []
    for i, b in enumerate(v[11:103]):
        trk = i
        for bit in range(8):
            if b & (1 << bit):
                free.append((trk, bit))
    print('    free sector count =', len(free))

    print('\n=== Catalog (T18,S1..S3) ===')
    c1 = read_sector(data, 18, 1)
    print('  catalog link T%d S%d (expect T17 S1)' % (c1[1], c1[2]))
    print('  entries/sector = %d (%02X)' % (c1[3], c1[3]))
    print('  file type      = %02X' % c1[11])
    print('  aux            = $%02X%02X' % (c1[13], c1[12]))
    print('  sectors used   = %d' % (c1[14] + c1[15] * 256))

    names = []
    for sec in (1, 2, 3):
        s = read_sector(data, 18, sec)
        for e in range(13):
            base = 11 + e * 35
            ent = s[base:base + 35]
            if ent[0] == 0:
                continue
            name = ''.join(chr(c & 0x7F) for c in ent[1:33]).rstrip()
            ft = ent[33]
            aux = (ent[35] << 8) | ent[34] if len(ent) > 35 else 0
            names.append((sec, e, name, ft, ent[11], ent[12] + ent[13] * 256))
    print('  file entries:')
    for sec, e, name, ft, start, nsec in names:
        print('    T18S%d#%02d  %-30s type=%02X start=T%d  sectors=%d  bytes=%d'
              % (sec, e, name, ft, start, nsec, nsec * SEC))
    print('  total files =', len(names))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else r'C:\dev\a2vera\a2vera_dos33.dsk')
