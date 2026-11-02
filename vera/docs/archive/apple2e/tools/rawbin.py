"""Extract the raw 6502 image from a `ld65 -t none` output for dos33.py.

`-t none` produces a flat binary whose first byte belongs at the cfg's
STARTADDRESS, so there is no AppleSingle header to read the load address from:
the caller states it, and it MUST equal STARTADDRESS.

Do NOT prepend the 4-byte BIN header here.  dos33.py writes
`load(LE) + length(LE) + data` itself, and DOS 3.3 BRUN consumes that header
without loading it -- the data lands exactly at the stated address.  Proven
against the kit's own dist/HGR.dsk: $6000 holds crt0's `CLD; TSX; STX`, not a
header.  Adding a header a second time shifts the whole image 4 bytes late and
every absolute address in it is then wrong, which is why main was never
reached.
"""
import io
import sys

def wrap(src, dst, load):
    data = io.open(src, 'rb').read()
    io.open(dst, 'wb').write(data)
    print('%s  load=$%04X  image=%d bytes  first=%s' %
          (src, load, len(data), ' '.join('%02X' % b for b in data[:4])))
    print('  -> %s (%d bytes, raw: dos33.py adds the BIN header)' % (dst, len(data)))

if __name__ == '__main__':
    wrap(sys.argv[1], sys.argv[2], int(sys.argv[3], 16))
