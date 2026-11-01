"""Verify a packed DOS 3.3 image by reading it back from the raw sectors.

dos33.py only writes; it has no read-back mode.  Packing bugs (the double
BIN-header class, a broken T/S chain, a length that does not match the sectors)
are invisible in the printed catalog, so this walks the real structures:
VTOC -> catalog -> T/S lists -> data sectors, then compares the stored bytes
with the source file that was packed.

DOS 3.3 layout (as written by C:\\dev\\pom2games\\dev\\tools\\dos33.py, which
places the VTOC on track 17 the way real DOS 3.3 does - track 1 is DOS code).
Tracks and sectors are printed in DECIMAL here; the bytes on disk are the same
numbers, so do not read them as hex.

  35 tracks x 16 sectors x 256 bytes, image in DOS (logical) sector order.
  VTOC   = track 17 sector 0:  b0 = 0x04, b1/b2 = first catalog sector,
                              b6 = volume, $34/$35 = tracks / sectors-per-track.
  Catalog = track 17 sectors 15..1, chained through b1/b2.
            Entries at 0x0B + k*35, k = 0..6:
              +0  T/S-list start track
              +1  T/S-list start sector
              +2  file type (high bit = locked)
              +3  name, 30 bytes, high bit set
              +33 sector count, 16-bit little endian
  T/S list sector: b1/b2 = next list sector ($00,$00 = none); data pairs start
                   at offset 0x0C, 122 pairs per sector.
"""

import struct
import sys

SECTORS = 16
TRACKS = 35
VTOC_T, VTOC_S = 17, 0
TYPES = {0x00: "T", 0x01: "I", 0x02: "A", 0x04: "B", 0x08: "R", 0x10: "D"}


def sec(img, tr, sn):
    off = tr * SECTORS * 256 + sn * 256
    return img[off:off + 256]


def read_disk(path):
    img = open(path, "rb").read()
    want = TRACKS * SECTORS * 256
    if len(img) != want:
        raise SystemExit("%s is %d bytes, expected %d" % (path, len(img), want))
    return img


def read_vtoc(img):
    v = sec(img, VTOC_T, VTOC_S)
    if v[0] != 0x04:
        raise SystemExit("VTOC signature is %02X, expected 04" % v[0])
    tr, sn = v[0x34], v[0x35]
    if (tr, sn) != (TRACKS, SECTORS):
        raise SystemExit("VTOC geometry is %d tracks x %d sectors" % (tr, sn))
    return v[6], (v[1], v[2])


def read_catalog(img):
    vol, cat = read_vtoc(img)
    entries = []
    seen = set()
    tr, sn = cat
    while (tr, sn) != (0, 0):
        if (tr, sn) in seen:
            raise SystemExit("catalog chain revisits T%d/S%d" % (tr, sn))
        seen.add((tr, sn))
        s = sec(img, tr, sn)
        for k in range(7):
            e = 0x0B + k * 35
            if s[e + 3] == 0:
                continue
            name = "".join(chr(b & 0x7F) for b in s[e + 3:e + 33]).rstrip()
            entries.append({
                "start": (s[e], s[e + 1]),
                "type": TYPES.get(s[e + 2] & 0x0F, "?%02X" % s[e + 2]),
                "locked": bool(s[e + 2] & 0x80),
                "name": name,
                "sectors": struct.unpack("<H", s[e + 33:e + 35])[0],
            })
        tr, sn = s[1], s[2]
    return vol, entries


def walk_ts_lists(img, start):
    """Follow the T/S chain; return (data sectors, list sector count).

    The catalog's sector count covers the T/S list sectors as well as the data
    sectors, so both are reported separately and checked against it.
    """
    data = []
    lists = 0
    tr, sn = start
    while (tr, sn) != (0, 0):
        if not (0 <= tr < TRACKS and 0 <= sn < SECTORS):
            raise SystemExit("T/S pair T%d/S%d is off the disk" % (tr, sn))
        lists += 1
        if lists > 64:
            raise SystemExit("T/S chain longer than the disk can hold")
        s = sec(img, tr, sn)
        for k in range(122):
            off = 0x0C + 2 * k
            t, x = s[off], s[off + 1]
            if (t, x) == (0, 0):
                break
            if not (0 <= t < TRACKS and 0 <= x < SECTORS):
                raise SystemExit("data pair T%d/S%d is off the disk" % (t, x))
            data.append((t, x))
        tr, sn = s[1], s[2]
    return data, lists


def gather(img, pairs):
    out = bytearray()
    for t, x in pairs:
        out += sec(img, t, x)
    return bytes(out)


def main():
    dsk = sys.argv[1]
    want = {}
    for a in sys.argv[2:]:
        name, path = a.split("=", 1)
        want[name.upper()] = path

    img = read_disk(dsk)
    vol, entries = read_catalog(img)
    print("%s: volume %s, %d catalog entries" % (dsk, vol, len(entries)))

    bad = 0
    claimed = {}
    for e in entries:
        pairs, lists = walk_ts_lists(img, e["start"])
        raw = gather(img, pairs)
        body = raw
        note = ""
        if e["type"] == "B":
            if len(raw) < 4:
                raise SystemExit("%s: BIN shorter than its 4-byte header" % e["name"])
            addr = raw[0] | (raw[1] << 8)
            ln = raw[2] | (raw[3] << 8)
            body = raw[4:4 + ln]
            note = "load $%04X  len %d" % (addr, ln)
        print("  %-9s %s%s  T/S T%d/S%d  %4d sect  %5d B  %s"
              % (e["name"], e["type"], "*" if e["locked"] else " ",
                 e["start"][0], e["start"][1], e["sectors"], len(body), note))
        if len(pairs) + lists != e["sectors"]:
            print("           !! chain has %d data + %d list = %d sectors, "
                  "catalog says %d" % (len(pairs), lists, len(pairs) + lists,
                                       e["sectors"]))
            bad += 1

        for key in pairs:
            claimed[key] = claimed.get(key, 0) + 1

        path = want.get(e["name"].upper())
        if path:
            src = open(path, "rb").read()
            if src == body:
                print("           == %s (%d B) exact" % (path, len(src)))
            else:
                print("           !! %s (%d B) DIFFERS (stored %d B)"
                      % (path, len(src), len(body)))
                for i in range(min(len(src), len(body))):
                    if src[i] != body[i]:
                        print("           first difference at %d: src %02X stored %02X"
                              % (i, src[i], body[i]))
                        break
                bad += 1

    dupes = sorted(k for k, v in claimed.items() if v > 1)
    if dupes:
        print("sectors claimed by more than one file: %s"
              % ", ".join("T%d/S%d" % k for k in dupes[:12]))
        bad += 1
    missing = sorted(set(want) - {e["name"].upper() for e in entries})
    if missing:
        print("requested files absent from the catalog: %s" % ", ".join(missing))
        bad += 1
    print("data sectors claimed: %d of %d usable"
          % (len(claimed), TRACKS * SECTORS - 3 * SECTORS))
    print("RESULT: %s" % ("OK" if bad == 0 else "%d problem(s)" % bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
