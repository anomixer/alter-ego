#!/usr/bin/env python3
"""Find the DOS 3.3 VTOC in a .dsk under .do (DOS order) vs .po (ProDOS order)."""
import sys

SEC, TRKS, SECS = 256, 35, 16
# DOS 3.3 4:3 sector interleave: logical -> physical (ProDOS order)
INTERLEAVE = [0, 4, 8, 12, 1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15]


def looks_like_vtoc(s):
    return (s[1] == 0x11 and s[2] == 0x0F and s[6] == 0x10 and s[7] == 0x23
            and s[8] == 0x10 and s[5] == 0x00)


def main(path):
    data = open(path, 'rb').read()
    print('bytes', len(data))
    for name, mapping in (('raw/.do', list(range(16))), ('.po->.do', INTERLEAVE),
                          ('.do->.po', [INTERLEAVE.index(i) for i in range(16)])):
        found = []
        for trk in range(TRKS):
            for sec in range(SECS):
                phys = mapping[sec]
                off = (trk * SECS + phys) * SEC
                s = data[off:off + SEC]
                if looks_like_vtoc(s):
                    found.append((trk, sec, s))
        print(f'{name}: VTOC candidates = {[(t, s) for t, s, _ in found]}')
        for trk, sec, s in found:
            print(f'  VTOC at logical T{trk} S{sec} (phys {mapping[sec]})')
            print('   bitmap T%d S%d' % (s[3], s[4]))
            print('   tracks=%d sectors/track=%d' % (s[7], s[8]))
            print('   sectors used = %d' % (s[14] + s[15] * 256))
            print('   hex[0:16] =', s[:16].hex(' '))
            return mapping


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else r'C:\dev\a2vera\a2vera\a2vera_dos33.dsk')
