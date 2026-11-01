"""Decode a tag-form RLE stream the way hgr.s's hgr_draw_screen does, and report
where the real decoder would stop.

tag = stream[0]
b != tag  -> literal: emit b, last = b
b == tag  -> n = next byte; n == 0 ends the stream, else emit `last` n times

Used to check the stream that is actually sitting in memory at load time against
the emitted byte count the HGR page needs (7,680).
"""
import sys


def decode(stream, limit=200000):
    if not stream:
        return 0, 0, 'empty'
    tag = stream[0]
    i = 1
    last = 0
    emitted = 0
    while i < len(stream):
        b = stream[i]
        i += 1
        if b != tag:
            emitted += 1
            last = b
        else:
            if i >= len(stream):
                return emitted, i, 'ran off the end looking for the run length'
            n = stream[i]
            i += 1
            if n == 0:
                return emitted, i, 'terminator found'
            emitted += n
        if emitted > limit:
            return emitted, i, 'emitted past the page budget'
    return emitted, i, 'stream exhausted without a terminator'


def main():
    path = sys.argv[1]
    data = open(path, 'rb').read()
    emitted, consumed, why = decode(data)
    print('file          : %s (%d bytes)' % (path, len(data)))
    print('tag           : $%02X' % data[0])
    print('emitted bytes : %d' % emitted)
    print('stream consumed: %d of %d' % (consumed, len(data)))
    print('outcome       : %s' % why)
    print('HGR page needs : 7680  ->  %s' % ('exact' if emitted == 7680 else 'MISMATCH'))


main()
