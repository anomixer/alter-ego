"""Extract the raw 6502 image from a cc65 AppleSingle output for dos33.py.

dos33.py writes the DOS 3.3 BIN header itself -- `load(LE) + length(LE) +
data` -- and DOS 3.3 BRUN consumes that header WITHOUT loading it, so the data
lands exactly at the stated address.  This tool must therefore emit area 1
verbatim; prepending a header here shifts the image 4 bytes late and breaks
every absolute address in it (verified against the kit's dist/HGR.dsk, where
$6000 holds crt0's first instruction, not a header).

What cc65's apple2 target actually emits (inspected in this session):
  magic 00 05 16 00, version 00 02 00 00, entry count at offset 24,
  12-byte big-endian (areaId, offset, length) entries from offset 26.
  area 1  = the raw 6502 image, starting with code, NOT with a BIN header
  area 11 = exec args, 8 bytes, whose last two bytes are the load address
            in BIG-endian ($0803 for the default apple2/cc65 load address)

So the load address comes from area 11 and the payload is area 1 verbatim.
The area-11 load address must equal the cfg's STARTADDRESS, and the @addr
passed to dos33.py must equal both.
"""
import argparse
import io
import struct


def read_apple_single(path):
    raw = io.open(path, 'rb').read()
    if raw[:4] != bytes([0x00, 0x05, 0x16, 0x00]):
        raise SystemExit('not an AppleSingle file: %s' % path)
    n = struct.unpack('>H', raw[24:26])[0]
    areas = {}
    for i in range(n):
        b = 26 + 12 * i
        aid = struct.unpack('>I', raw[b:b + 4])[0]
        off = struct.unpack('>I', raw[b + 4:b + 8])[0]
        ln = struct.unpack('>I', raw[b + 8:b + 12])[0]
        areas[aid] = raw[off:off + ln]

    data = areas.get(1)
    if data is None:
        raise SystemExit('area 1 (the 6502 image) missing in %s' % path)

    args = areas.get(11)
    if args is None or len(args) < 2:
        raise SystemExit('area 11 (exec args) missing in %s' % path)
    load = struct.unpack('>H', args[-2:])[0]
    return load, data, args


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', help='cc65 AppleSingle output')
    ap.add_argument('out', help='DOS 3.3 BIN payload to write')
    ap.add_argument('--load', type=lambda s: int(s, 16), default=None,
                    help='override the load address, hex (e.g. 6000)')
    a = ap.parse_args()

    load, data, args = read_apple_single(a.src)
    if a.load is not None:
        load = a.load
    if len(data) > 0xFFFF:
        raise SystemExit('payload %d bytes exceeds the 16-bit BIN length' % len(data))

    io.open(a.out, 'wb').write(data)
    print('%s' % a.src)
    print('  exec args : %s' % ' '.join('%02X' % b for b in args))
    print('  load=$%04X  image=%d bytes  first=%s'
          % (load, len(data), ' '.join('%02X' % b for b in data[:4])))
    print('  -> %s (%d bytes, raw: dos33.py adds the BIN header)' % (a.out, len(data)))


if __name__ == '__main__':
    main()
