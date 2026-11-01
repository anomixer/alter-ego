"""Report a DOS 3.3 file's stored load address and head bytes from a .dsk image.

Why this exists: DOS 3.3's BRUN loads a type-A binary to the load address recorded
in its catalog entry and jumps there.  Every on-screen channel available on this
host is ambiguous (with HIRES active CHROUT text is not shown; the HGR page reads
as unwritten), so the handoff has to be checked offline.  The entry's load address
and the file's first bytes are exactly what decides whether the program starts.

Catalog entry layout, 7 entries per sector starting at offset $0B (this matches
tools/a2_dsk_verify.py, which is the tool that already validates this disk):
  +0  start track          +1  start sector
  +2  locked / type byte   +3  30-char name
  +21 file length in 512-byte blocks (2 bytes)
  +23 file type ($00=A, $80=B, $01=T, $04=I)
  +25 LOAD ADDRESS (2 bytes, little endian)
  +33 sectors used
"""
import sys
sys.path.insert(0, r'C:\dev\alter-ego\tools')
from a2_dsk_verify import read_disk, read_catalog, walk_ts_lists, gather, sec


def main():
    img_path, want = sys.argv[1], sys.argv[2].upper()
    img = read_disk(img_path)
    vol, entries = read_catalog(img)
    print("volume %d, catalog entries %d" % (vol, len(entries)))

    # Walk the catalog chain itself: the entry bytes live in catalog sectors, not
    # in the file's data sectors.
    from a2_dsk_verify import read_vtoc
    vol, cat = read_vtoc(img)
    tr, sn = cat
    seen = set()
    while (tr, sn) != (0, 0):
        if (tr, sn) in seen:
            break
        seen.add((tr, sn))
        s = sec(img, tr, sn)
        for k in range(7):
            off = 0x0B + k * 35
            if s[off + 3] == 0:
                continue
            nm = "".join(chr(b & 0x7F) for b in s[off + 3:off + 33]).rstrip()
            if nm != want:
                continue
            # DOS 3.3 stores these fields BIG-endian:
            #   +$21/$22 file length in 512-byte blocks
            #   +$23       file type ($00=A, $80=B, $01=T, $04=I)
            #   +$26/$27   LOAD ADDRESS  <- what BRUN loads to and jumps to
            #   +$2C/$2D   sectors used
            #
            # Measured, and this is the part that matters: the load address in the
            # CATALOG is not what BRUN uses.  BRUN reads the 4-byte header that
            # precedes the file's data, which the packer writes as
            # struct.pack("<HH", load, len) - little-endian, matching the pom2games
            # kit's own dos33.py/build_disk.py.  Reading the catalog fields above
            # with the wrong offsets/endianess produced nonsense ($C3CF, blocks
            # 12544) and a false root cause.  The header is authoritative:
            # AE2GAME -> 00 60 d2 2f = load $6000, len $2FD2 = 12242.
            blocks = (s[off + 0x21] << 8) | s[off + 0x22]
            ftype = s[off + 0x23]
            load = (s[off + 0x26] << 8) | s[off + 0x27]
            used = (s[off + 0x2C] << 8) | s[off + 0x2D]
            start = (s[off], s[off + 1])
            print("FOUND %-10s type $%02X  load $%04X  blocks %d  sectors %d  start T%d/S%d"
                  % (nm, ftype, load, blocks, used, start[0], start[1]))
            data, lists = walk_ts_lists(img, start)
            body = gather(img, data)
            print("  data sectors %d (list sectors %d) -> %d bytes"
                  % (len(data), lists, len(body)))
            print("  first 48 bytes: %s" % body[:48].hex(" "))
            # Decode the 4-byte DOS 3.3 header the packer writes:
            # struct.pack("<HH", load, len).  This is what BRUN acts on.
            hload = body[0] | (body[1] << 8)
            hlen = body[2] | (body[3] << 8)
            print("  DOS header: load $%04X  len %d  (payload after header %d bytes)"
                  % (hload, hlen, len(body) - 4))
            return
        tr, sn = s[1], s[2]
    print("%s not found" % want)
    print("names: %s" % " ".join(x["name"] for x in entries).encode("ascii", "replace").decode("ascii"))


if __name__ == "__main__":
    main()
