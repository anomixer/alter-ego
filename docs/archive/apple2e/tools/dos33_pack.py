#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apple II DOS 3.3 disk image packer (143360 = 35*16*256), stdlib only.

Format facts below were verified against primary sources, not memory:
  * deater/dos33fsprogs  utils/dos33fs-utils/dos33.h        (field offsets)
  * deater/dos33fsprogs  utils/dos33fs-utils/dos33.c        (SAVE algorithm)
  * deater/dos33fsprogs  utils/dos33fs-utils/dos33_vtoc_bitmap.c (bitmap polarity)
  * deater/dos33fsprogs  utils/dos33fs-utils/make_b.c       (BIN 4-byte header)
  * deater/dos33fsprogs  utils/dos33fs-utils/dos33_raw.c    (4:3 interleave table)
  * deater/dos33fsprogs  empty_disk/empty.dsk               (real INITed disk bytes)
  * cc65/cc65            libsrc/apple2/exehdr.s             (AppleSingle v2 header)
"""
import argparse
import sys

TRACKS, SECTORS, BPS = 35, 16, 256
DISK_BYTES = TRACKS * SECTORS * BPS          # 143360

VTOC_T, VTOC_S = 17, 0
CATALOG_T, CATALOG_FIRST_S, CATALOG_SECTORS = 17, 15, 15

# --- VTOC field offsets (on-disk byte offsets inside T17,S0) -----------------
# Verified byte-for-byte against deater's dos33.h AND against the real
# DOS-3.3-INITed image empty_disk/empty.dsk (T17,S0 = 00 11 0F 03 00 00 FE ..):
#   0x01=0x11=17 -> catalog track (catalog content really is at T17)
#   0x02=0x0F=15 -> catalog sector (T17,S15 really holds the first catalog sector)
#   0x03=03      -> DOS release 3
#   0x06=0xFE    -> volume 254
#   0x27=0x7A    -> 122 max T/S pairs per TSL sector
#   0x34=0x23,0x35=0x10,0x36/37=0x0100 -> 35 tracks x 16 sectors x 256 bytes
#   0x38..       -> bitmap; T17 S0 used, T17 S12..15 used (= the 4 catalog
#                   sectors of the chain), T18 S14,S15 used (= HELLO data+TSL)
V_NEXT_VTOC_T = 0x00                         # 0 = no chained VTOC
V_CATALOG_T, V_CATALOG_S = 0x01, 0x02
V_DOS_RELEASE = 0x03                         # 3 bytes: 3,0,0
V_VOLUME = 0x06
V_MAX_TS_PAIRS = 0x27                        # = 122
V_LAST_ALLOC_T, V_ALLOC_DIR = 0x30, 0x31
V_NUM_TRACKS, V_SECTORS_TRACK = 0x34, 0x35
V_BYTES_SL, V_BYTES_SH = 0x36, 0x37
V_BITMAP = 0x38                              # 4 bytes per track
MAX_TS_PAIRS = 122

# --- catalog ---------------------------------------------------------------
CAT_NEXT_T, CAT_NEXT_S = 0x01, 0x02
CAT_FILE_LIST = 0x0B                         # first entry at byte 11
ENT_SIZE = 0x23                              # 35 bytes -> 7 entries/sector
ENT_PER_SEC = 7
E_TS_T, E_TS_S, E_TYPE = 0, 1, 2            # +0 TSL track, +1 TSL sector, +2 type
E_NAME, NAME_LEN = 3, 30                     # +3..32 high-ASCII, space padded
E_SIZE_L, E_SIZE_H = 0x21, 0x22              # +33/+34 sectors used (LE)

# DOS 3.3 catalog type byte is a bit field (dos33_char_to_type):
TYPE = {'T': 0x00, 'I': 0x01, 'A': 0x02, 'B': 0x04,
        'S': 0x08, 'R': 0x10, 'N': 0x20, 'L': 0x40}

# --- TSL -------------------------------------------------------------------
T_NEXT_T, T_NEXT_S = 0x01, 0x02
T_OFFSET_L, T_OFFSET_H = 0x05, 0x06
T_LIST, T_ENTRY_SIZE = 0x0C, 0x02            # list starts at byte 12, 122 pairs

# 4:3 interleave: DOS logical sector -> physical sector in a .po image.
# (dos33_raw.c: "static int dos33_sector_map[16]={0,7,14,6,13,5,12,4,11,3,10,2,9,1,8,15}")
PRODOS_TO_DOS = [0, 7, 14, 6, 13, 5, 12, 4, 11, 3, 10, 2, 9, 1, 8, 15]


class Disk(object):
    def __init__(self, po=False):
        self.buf = bytearray(DISK_BYTES)
        self.po = po

    def off(self, t, s):
        return (t * SECTORS + (PRODOS_TO_DOS[s] if self.po else s)) * BPS

    def rsec(self, t, s):
        o = self.off(t, s)
        sec = self.buf[o:o + BPS]
        return sec if len(sec) == BPS else bytes(sec) + bytes(BPS - len(sec))

    def wsec(self, t, s, data):
        o = self.off(t, s)
        self.buf[o:o + BPS] = bytes(bytearray(data)[:BPS])


# --- sector allocation bitmap: bit==1 means FREE (dos33_vtoc_bitmap.c) -------
def bm_free(v, t, s):
    b = V_BITMAP + t * 4
    return ((v[b + 1] if s < 8 else v[b]) >> (s if s < 8 else s - 8)) & 1


def bm_reserve(v, t, s):
    b = V_BITMAP + t * 4
    if s < 8:
        v[b + 1] &= ~(1 << s) & 0xFF
    else:
        v[b] &= ~(1 << (s - 8)) & 0xFF


def bm_all_free(v):
    for t in range(TRACKS):
        v[V_BITMAP + t * 4] = 0xFF
        v[V_BITMAP + t * 4 + 1] = 0xFF


class Cursor(object):
    """Deterministic allocator: T18 S0 forward, wrapping, never track 0."""
    def __init__(self, v):
        self.v = v
        self.t, self.s = 18, 0

    def take(self):
        for _ in range(TRACKS * SECTORS):
            t, s = self.t, self.s
            self.s += 1
            if self.s >= SECTORS:
                self.s = 0
                self.t += 1
            if self.t >= TRACKS:
                self.t = 18
            if t == 0:
                continue
            if bm_free(self.v, t, s):
                bm_reserve(self.v, t, s)
                return (t, s)
        raise RuntimeError("no free sectors")


def new_vtoc(volume=254):
    v = bytearray(BPS)
    v[V_NEXT_VTOC_T] = 0                       # no chained VTOC
    v[V_CATALOG_T] = CATALOG_T
    v[V_CATALOG_S] = CATALOG_FIRST_S
    v[V_DOS_RELEASE] = 3
    v[V_VOLUME] = volume & 0xFF
    v[V_MAX_TS_PAIRS] = MAX_TS_PAIRS
    v[V_LAST_ALLOC_T] = CATALOG_T
    v[V_ALLOC_DIR] = 1
    v[V_NUM_TRACKS] = TRACKS
    v[V_SECTORS_TRACK] = SECTORS
    v[V_BYTES_SL] = BPS & 0xFF
    v[V_BYTES_SH] = (BPS >> 8) & 0xFF
    bm_all_free(v)
    for s in range(SECTORS):                       # track 0 = EOF sentinel
        bm_reserve(v, 0, s)
    bm_reserve(v, VTOC_T, VTOC_S)                  # the VTOC itself
    return v


def build_catalog(d, v):
    """15 catalog sectors, T17 S15 -> S14 -> ... -> S1 -> (0,0)."""
    secs = [(CATALOG_T, CATALOG_FIRST_S - i) for i in range(CATALOG_SECTORS)]
    for i, (t, s) in enumerate(secs):
        bm_reserve(v, t, s)
        sec = bytearray(BPS)
        if i + 1 < len(secs):
            sec[CAT_NEXT_T] = secs[i + 1][0]
            sec[CAT_NEXT_S] = secs[i + 1][1]
        d.wsec(t, s, sec)
    return secs


def add_file(d, v, cur, name, payload, ftype_byte, locked=False):
    n = (len(payload) + BPS - 1) // BPS
    tslist, data = [], []
    for i in range(n):
        if i % MAX_TS_PAIRS == 0:
            tslist.append(cur.take())
        data.append(cur.take())

    for k, ts in enumerate(tslist):
        sec = bytearray(BPS)
        base = k * MAX_TS_PAIRS
        cnt = min(MAX_TS_PAIRS, n - base)
        sec[T_OFFSET_L] = base & 0xFF
        sec[T_OFFSET_H] = (base >> 8) & 0xFF
        for j in range(cnt):
            t, s = data[base + j]
            sec[T_LIST + j * 2] = t
            sec[T_LIST + j * 2 + 1] = s
        if k + 1 < len(tslist):
            sec[T_NEXT_T] = tslist[k + 1][0]
            sec[T_NEXT_S] = tslist[k + 1][1]
        d.wsec(ts[0], ts[1], sec)

    for i, (t, s) in enumerate(data):
        chunk = payload[i * BPS:(i + 1) * BPS]
        d.wsec(t, s, chunk + bytes(BPS - len(chunk)))

    # find a free catalog slot (start-track byte == 0x00 free, 0xFF deleted)
    t, s = v[V_CATALOG_T], v[V_CATALOG_S]
    while True:
        sec = bytearray(d.rsec(t, s))
        for i in range(ENT_PER_SEC):
            b = CAT_FILE_LIST + i * ENT_SIZE
            if sec[b] in (0x00, 0xFF):
                nm = name.upper().encode('ascii')
                if len(nm) > NAME_LEN:
                    raise SystemExit("name too long (max 30): %s" % name)
                if nm[0] < 0x40:
                    raise SystemExit("first char must be >= 'A': %s" % name)
                sec[b + E_TS_T] = tslist[0][0]
                sec[b + E_TS_S] = tslist[0][1]
                sec[b + E_TYPE] = (ftype_byte | 0x80) if locked else ftype_byte
                for x in range(NAME_LEN):
                    c = nm[x] if x < len(nm) else 0x20
                    sec[b + E_NAME + x] = c ^ 0x80
                used = len(tslist) + len(data)
                sec[b + E_SIZE_L] = used & 0xFF
                sec[b + E_SIZE_H] = (used >> 8) & 0xFF
                d.wsec(t, s, sec)
                v[V_LAST_ALLOC_T] = data[-1][0]
                return used
        nt, ns = sec[CAT_NEXT_T], sec[CAT_NEXT_S]
        if nt == 0 and ns == 0:
            raise SystemExit("catalog full")
        t, s = nt, ns


# --- cc65 AppleSingle v2 (cc65 libsrc/apple2/exehdr.s) ----------------------
def parse_apple_single(raw):
    """Return (data_fork_bytes, load_address, prodos_type)."""
    if raw[:4] != bytes([0x00, 0x05, 0x16, 0x00]):
        raise SystemExit("not AppleSingle v2 (magic 00 05 16 00)")
    n = raw[24] * 256 + raw[25]                   # "Number of entries" at offset 24
    ents = []
    for i in range(n):
        o = 26 + i * 12                            # app_id, off, len (3x 4-byte BE)
        if o + 12 > len(raw):
            break
        aid = int.from_bytes(raw[o:o + 4], 'big')
        off = int.from_bytes(raw[o + 4:o + 8], 'big')
        ln = int.from_bytes(raw[o + 8:o + 12], 'big')
        ents.append((aid, off, ln))
    d = next((e for e in ents if e[0] == 1), None)
    if d is None:
        raise SystemExit("AppleSingle: no Data Fork entry (aid 1)")
    if d[1] + d[2] != len(raw):
        print("  warn: data fork %d+%d != file %d" % (d[1], d[2], len(raw)))
    fork = raw[d[1]:d[1] + d[2]]
    load, ftype = None, None
    for aid, off, ln in ents:                      # aid 11 = ProDOS File Info (8 bytes)
        if aid == 11 and ln >= 8:
            ftype = int.from_bytes(raw[off + 2:off + 4], 'big')
            load = int.from_bytes(raw[off + 6:off + 8], 'big')
        if aid == 4 and ln >= 10:                  # aid 4 = Execution
            load = int.from_bytes(raw[off + 6:off + 8], 'big')
    return fork, load, ftype


# --- reader used by --verify -------------------------------------------------
def read_catalog(d, v):
    out, t, s = [], v[V_CATALOG_T], v[V_CATALOG_S]
    seen = set()
    while (t, s) != (0, 0) and (t, s) not in seen:
        seen.add((t, s))
        sec = d.rsec(t, s)
        for i in range(ENT_PER_SEC):
            b = CAT_FILE_LIST + i * ENT_SIZE
            st = sec[b]
            if st in (0x00, 0xFF):
                continue
            nm = ''.join(chr(c ^ 0x80) for c in sec[b + E_NAME:b + E_NAME + NAME_LEN])
            out.append(dict(ts_t=st, ts_s=sec[b + E_TS_S], type=sec[b + E_TYPE],
                            name=nm.rstrip('\xa0').strip(),
                            used=sec[b + E_SIZE_L] + (sec[b + E_SIZE_H] << 8),
                            cat=(t, s), slot=i))
        t, s = sec[CAT_NEXT_T], sec[CAT_NEXT_S]
    return out


def read_file(d, e):
    payload = bytearray()
    t, s = e['ts_t'], e['ts_s']
    seen = set()
    while (t, s) != (0, 0) and (t, s) not in seen:
        seen.add((t, s))
        sec = d.rsec(t, s)
        for j in range(MAX_TS_PAIRS):
            o = T_LIST + j * 2
            if sec[o] == 0 and sec[o + 1] == 0:
                break
            payload += d.rsec(sec[o], sec[o + 1])
        t, s = sec[T_NEXT_T], sec[T_NEXT_S]
    return bytes(payload)


def main():
    ap = argparse.ArgumentParser(description="Apple II DOS 3.3 disk packer")
    ap.add_argument('out', help="output .dsk image (143360 bytes)")
    ap.add_argument('--add', nargs=2, action='append', metavar=('NAME', 'FILE'),
                    help="add NAME from FILE (repeatable)")
    ap.add_argument('--apple-single', action='store_true',
                    help="last --add FILE is a cc65 AppleSingle")
    ap.add_argument('--type', default='B', help="DOS 3.3 type: B IN A S R N L T")
    ap.add_argument('--load', type=lambda x: int(x, 0), default=None,
                    help="BIN load address (default: from AppleSingle, else $2000)")
    ap.add_argument('--po', action='store_true',
                    help="write ProDOS (.po) sector order; default is DOS (.do) order")
    ap.add_argument('--volume', type=int, default=254)
    ap.add_argument('--base', help="start from an existing .dsk (keeps DOS and its "
                                   "files; new files use its VTOC bitmap/catalog)")
    ap.add_argument('--verify', action='store_true')
    a = ap.parse_args()

    d = Disk(po=a.po)
    if a.base:
        raw = open(a.base, 'rb').read()
        if len(raw) != TRACKS * SECTORS * BPS:
            raise SystemExit("base image is not 143360 bytes")
        d.buf = bytearray(raw)
        v = bytearray(d.rsec(VTOC_T, VTOC_S))
        print("base %s: VTOC T%d/S%d  volume %d  %dx%d  catalog T%d/S%d"
              % (a.base, VTOC_T, VTOC_S, v[V_VOLUME], v[V_NUM_TRACKS],
                 v[V_SECTORS_TRACK], v[V_CATALOG_T], v[V_CATALOG_S]))
        free = sum(bm_free(v, t, s) for t in range(TRACKS) for s in range(SECTORS))
        print("base free sectors: %d (%d bytes)" % (free, free * BPS))
    else:
        v = new_vtoc(a.volume)
        build_catalog(d, v)
    cur = Cursor(v)
    jobs, expected = [], []

    for name, path in (a.add or []):
        raw = open(path, 'rb').read()
        single = a.apple_single or raw[:4] == bytes([0x00, 0x05, 0x16, 0x00])
        if single:
            fork, load, ftype = parse_apple_single(raw)
            load = a.load if a.load is not None else (load if load else 0x2000)
            print("%-8s AppleSingle data fork %d bytes, load $%04X, ProDOS type $%04X"
                  % (name, len(fork), load, ftype or 0))
            payload = bytes([load & 0xFF, (load >> 8) & 0xFF,
                             len(fork) & 0xFF, (len(fork) >> 8) & 0xFF]) + fork
        else:
            load = a.load if a.load is not None else 0x2000
            print("%-8s raw %d bytes, load $%04X" % (name, len(raw), load))
            payload = bytes([load & 0xFF, (load >> 8) & 0xFF,
                             len(raw) & 0xFF, (len(raw) >> 8) & 0xFF]) + raw
        jobs.append((name, payload))

    for name, payload in jobs:
        used = add_file(d, v, cur, name, payload, TYPE[a.type.upper()])
        expected.append((name, payload))
        print("added %-8s %5d sectors (%d data + header)" % (name, used, used - 1))

    d.wsec(VTOC_T, VTOC_S, v)
    with open(a.out, 'wb') as f:
        f.write(d.buf)
    print("wrote %s  %d bytes  %s order"
          % (a.out, len(d.buf), '.po/ProDOS' if a.po else '.do/DOS'))

    if a.verify:
        r = Disk(po=a.po)
        r.buf = bytearray(open(a.out, 'rb').read())
        rv = r.rsec(VTOC_T, VTOC_S)
        assert len(r.buf) == DISK_BYTES, "size"
        assert rv[V_NUM_TRACKS] == TRACKS and rv[V_SECTORS_TRACK] == SECTORS, "geometry"
        assert rv[V_DOS_RELEASE] == 3, "dos release"
        print("verify: VTOC T%d/S%d vol %d  %d tracks x %d sectors  maxTS %d"
              % (VTOC_T, VTOC_S, rv[V_VOLUME], rv[V_NUM_TRACKS],
                 rv[V_SECTORS_TRACK], rv[V_MAX_TS_PAIRS]))
        entries = read_catalog(r, rv)
        ok = True
        for e in entries:
            blob = read_file(r, e)
            want = dict(expected).get(e['name'])
            status = "MISSING"
            if want is not None:
                pad = len(blob) - len(want)
                same = blob[:len(want)] == want and pad >= 0 and blob[len(want):] == bytes(pad)
                status = "OK  " if same else "DIFF"
                ok = ok and same
            print("  %s  %-6s type $%02X  %3d sectors  TSL T%d/S%d  cat T%d/S%d  "
                  "%d bytes (%d pad)"
                  % (status, e['name'], e['type'], e['used'], e['ts_t'], e['ts_s'],
                     e['cat'][0], e['cat'][1], len(blob), len(blob) - len(want or b'')))
            if want is not None and blob[:len(want)] != want:
                for i in range(min(len(blob), len(want))):
                    if blob[i] != want[i]:
                        print("      first diff at %d: got %02X want %02X"
                              % (i, blob[i], want[i]))
                        break
        for name, payload in expected:
            if name not in [e['name'] for e in entries]:
                print("  MISSING %s" % name)
                ok = False
        free = sum(bm_free(rv, t, s) for t in range(TRACKS) for s in range(SECTORS))
        print("verify: %d free sectors (%d bytes)" % (free, free * BPS))
        # every sector referenced by a file must be marked used in the bitmap
        refs = set([(VTOC_T, VTOC_S)])
        ct, cs = rv[V_CATALOG_T], rv[V_CATALOG_S]
        cseen = set()
        while (ct, cs) != (0, 0) and (ct, cs) not in cseen:
            cseen.add((ct, cs))
            refs.add((ct, cs))
            csec = r.rsec(ct, cs)
            ct, cs = csec[CAT_NEXT_T], csec[CAT_NEXT_S]
        for e in entries:
            t, s = e['ts_t'], e['ts_s']
            seen = set()
            while (t, s) != (0, 0) and (t, s) not in seen:
                seen.add((t, s))
                refs.add((t, s))
                sec = r.rsec(t, s)
                for j in range(MAX_TS_PAIRS):
                    o = T_LIST + j * 2
                    if sec[o] == 0 and sec[o + 1] == 0:
                        break
                    refs.add((sec[o], sec[o + 1]))
                t, s = sec[T_NEXT_T], sec[T_NEXT_S]
        unmarked = [x for x in sorted(refs) if bm_free(rv, x[0], x[1])]
        if unmarked:
            ok = False
            print("verify: bitmap does not mark used: %s" % unmarked[:8])
        print("verify: %d sectors referenced by catalog/TSL/data, all marked used: %s"
              % (len(refs), "yes" if not unmarked else "no"))
        print("VERIFY %s" % ("PASS" if ok else "FAIL"))
        if not ok:
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
