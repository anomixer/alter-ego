import sys, os
sys.path.insert(0, r'C:\dev\alter-ego\tools')
import a2_assets as A

main = open(r'C:\dev\alter-ego\build\dhgr_screen0_main.bin', 'rb').read()
aux = open(r'C:\dev\alter-ego\build\dhgr_screen0_aux.bin', 'rb').read()
print('raw main=%d aux=%d total=%d' % (len(main), len(aux), len(main) + len(aux)))

enc_main = A.rle_encode_screen(main)
enc_aux = A.rle_encode_screen(aux)
print('rle main=%d aux=%d total=%d' % (len(enc_main), len(enc_aux), len(enc_main) + len(enc_aux)))

d_main = A.decode_rle(enc_main)
d_aux = A.decode_rle(enc_aux)
print('decoded main=%d aux=%d' % (len(d_main), len(d_aux)))
print('main round trip exact:', d_main == main)
print('aux  round trip exact:', d_aux == aux)
print('main round trip + trailing 0:', d_main == main + b'\x00')
print('aux  round trip + trailing 0:', d_aux == aux + b'\x00')

# the emitted .s files must contain exactly the RLE byte counts
for path, names in ((r'C:\dev\alter-ego\build\dhgr_screen0.s', ('dhgr_screen0_main', 'dhgr_screen0_aux')),
                    (r'C:\dev\alter-ego\build\dhgr_tiles.s', ('dhgr_tiles',)),
                    (r'C:\dev\alter-ego\build\dhgr_spr.s', ('dhgr_spr',))):
    txt = open(path, encoding='utf-8').read()
    import re
    blocks = re.split(r'^_(\w+):$', txt, flags=re.M)
    labels = blocks[1::2]
    counts = [len(re.findall(r'\$[0-9A-F]{2}', b)) for b in blocks[2::2]]
    print(os.path.basename(path), 'labels=', labels, 'bytes=', counts)

# geometry cross-check against the reference formula, page 2 as well
for base in (0x20, 0x40):
    rows = [A.hgr_row(base, y) for y in range(192)]
    print('base $%04X: rows $%04X..$%04X, distinct=%d, span=%d'
          % (base << 8, min(rows), max(rows), len(set(rows)), max(rows) - min(rows) + 40))
A.selfcheck_layout(0x40, verbose=False)
print('page-2 layout self-check OK')

# every emitted tile/sprite byte must be < 0x80 (HGR/DHGR byte MSB rule)
tiles = A.chr_tiles(open(r'C:\dev\alter-ego\src\tileset.chr', 'rb').read())
tb = b''.join(A.tile_to_dhgr(t) for t in tiles)
sp = b''.join(A.sprite_to_dhgr(tiles, t) for t in range(0x90, 0x98, 2))
print('tile bytes max=%02X  sprite bytes max=%02X' % (max(tb), max(sp)))
lines = A.join_page(main, aux)
print('screen bytes max=%02X' % max(max(l) for l in lines))
print('screen colour histogram (cells):',
      sorted({A.read_cell(l, c) for l in lines for c in range(140)}))
