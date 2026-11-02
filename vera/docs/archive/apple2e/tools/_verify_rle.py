import sys
sys.path.insert(0, r'C:\dev\alter-ego\tools')
import a2_assets as A

# decoder semantics (neslib.s:334-372 / dhgr.s dhgr_draw_screen):
#   tag = data[0]; literal -> emit + last = b; (tag,n) -> emit last n times; (tag,0) -> END
cases = {
    'AAA BBB': b'AAABBB',
    'literal FF': b'\x00\xFF\x00',
    'run then FF': b'\x41\x41\x41\x41\xFF\x41',
}
for name, raw in cases.items():
    enc = A.rle_encode_screen(raw)
    try:
        dec = A.decode_rle(enc)
    except Exception as e:
        dec = 'EXC ' + repr(e)
    print('%-14s raw=%s enc=%s dec=%s' % (name, raw.hex(), enc.hex(),
                                          dec.hex() if isinstance(dec, bytes) else dec))

# tail behaviour: does the stream self-terminate?
raw = b'\x01\x02\x03'
enc = A.rle_encode_screen(raw)
print('tail enc =', enc.hex(), '-> dec =', A.decode_rle(enc).hex(), '(raw', raw.hex() + ')')

# does the HGR screen contain 0xFF bytes (tag collision)?
tiles = A.chr_tiles(open(r'C:\dev\alter-ego\src\tileset.chr', 'rb').read())
maps = [A.decode_rle(A.parse_c_array(r'C:\dev\alter-ego\src\map%d.h' % i)) for i in range(26)]
ff = [sum(1 for b in A.build_hgr_screen(tiles, m) if b == 0xFF) for m in maps]
print('HGR screens: 0xFF byte counts per level =', ff[:8], '... max=', max(ff))
free = []
for m in maps:
    used = set(A.build_hgr_screen(tiles, m))
    free.append(0xFF not in used)
print('levels where 0xFF is unused in the HGR screen:', sum(free), '/ 26')
