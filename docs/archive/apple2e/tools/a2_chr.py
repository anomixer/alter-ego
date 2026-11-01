import sys
from PIL import Image
blob = open(r'src\tileset.chr', 'rb').read()
# Render tile 0 and tile 1 as 8x8, both bit orders
def render_tile(t, path, bitfirst):
    im = Image.new("RGB", (8, 8))
    px = im.load()
    for r in range(8):
        lo = blob[t*16 + r*2]
        hi = blob[t*16 + r*2 + 1]
        for p in range(8):
            # NES CHR: bit0 = leftmost pixel. pixel p = bit p.
            # bitfirst True: use bit (7-p) [reversed]; False: use bit p.
            if bitfirst:
                v = ((hi >> (7-p)) & 1) << 1 | ((lo >> (7-p)) & 1)
            else:
                v = ((hi >> p) & 1) << 1 | ((lo >> p) & 1)
            if v:
                px[p, r] = (255,255,255) if v==3 else (128,128,128)
            else:
                px[p, r] = (0,0,0)
    im.save(path)
    return im
# Also make a montage of first 16 tiles both ways
for t in range(16):
    render_tile(t, r'build\a2\chr_t%d_bp.png' % t, True)
    render_tile(t, r'build\a2\chr_t%d_p.png' % t, False)
print("chr size:", len(blob), "bytes =", len(blob)//16, "tiles")
print("rendered tiles 0-15 both bit orders")
