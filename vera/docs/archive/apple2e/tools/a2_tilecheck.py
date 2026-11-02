import sys
from a2_assets import chr_tiles
# dump tile 0..3 of hgr_tiles.bin
tiles = open(r'build\hgr_tiles.bin','rb').read()
for t in range(4):
    b = tiles[t*8:t*8+8]
    print("hgr tile %d: %s" % (t, ' '.join('%02X' % x for x in b)))
# dump chr_tiles rows for tile 0..3
blob = open(r'src\tileset.chr','rb').read()
rows_list = chr_tiles(blob)
for t in range(4):
    rows = rows_list[t]
    print("chr tile %d rows (4bit): %s" % (t, ' '.join('%X' % (x & 0xF) for x in rows)))
