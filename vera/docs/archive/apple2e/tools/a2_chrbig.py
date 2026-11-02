import sys
from PIL import Image
blob = open(r'src\tileset.chr', 'rb').read()
SCALE = 16
def render(t, path, bitfirst):
    im = Image.new("RGB", (8*SCALE, 8*SCALE))
    px = im.load()
    for r in range(8):
        lo = blob[t*16 + r*2]
        hi = blob[t*16 + r*2 + 1]
        for p in range(8):
            if bitfirst:
                v = ((hi >> (7-p)) & 1) << 1 | ((lo >> (7-p)) & 1)
            else:
                v = ((hi >> p) & 1) << 1 | ((lo >> p) & 1)
            col = (255,255,255) if v==3 else ((128,128,128) if v==2 else ((64,64,64) if v==1 else (0,0,0)))
            for dy in range(SCALE):
                for dx in range(SCALE):
                    px[p*SCALE+dx, r*SCALE+dy] = col
    im.save(path)
for t in (1,):
    render(t, r'build\a2\chrbig_t1_p.png', False)   # pixel p = bit p
    render(t, r'build\a2\chrbig_t1_bp.png', True)   # pixel p = bit 7-p
print("done")
