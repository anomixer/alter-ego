import sys
sys.path.insert(0, r'C:\dev\alter-ego\tools')
from PIL import Image
import a2_assets as A

blob = open(r'src\tileset.chr','rb').read()

def chr_rows(blob, rev):
    """Return list of 512 tiles, each 8x8 pixel rows (value 0..3 per pixel).
    rev=True: rows[p]=pixel(7-p) (bit-reversed). rev=False: rows[p]=pixel p."""
    out=[]
    for t in range(512):
        rows=[]
        for r in range(8):
            lo=blob[t*16+r*2]; hi=blob[t*16+r*2+1]
            row=[]
            for p in range(8):
                bit = (7-p) if rev else p
                v=((hi>>bit)&1)<<1 | ((lo>>bit)&1)
                row.append(v)
            rows.append(row)
        out.append(rows)
    return out

def tile_to_hgr(rows, rowsel, bitfirst):
    """rows: 8x8 pixel rows. rowsel='p': rows[p]; '7p': rows[7-p].
    bitfirst=True: pixel k at bit 6-k (bit6=leftmost). False: bit k (bit0=leftmost)."""
    out=[]
    for t in range(512):
        tile=[]
        for r in range(8):
            v=0
            for k in range(7):
                idx = k if rowsel=='p' else (7-k)
                if rows[t][r][idx]:
                    b = (6-k) if bitfirst else k
                    v |= 1<<b
            if v==0x7F: v=0xFF
            tile.append(v)
        out.append(tile)
    return out

# nametable from a2_assets (reuse its tile list)
NT = A.nametable() if hasattr(A,'nametable') else None

# build hgr page: 32x30 nt, 40 bytes/line, tile=1 byte at byte col
COLS=32
def build_page(hgr_tiles, nt):
    page=bytearray(192*40)
    for idx,tile in enumerate(nt):
        col,row=idx%COLS, idx//COLS
        if col>=40: continue
        out_row=row-0
        if out_row<0 or out_row>=192//8: continue
        b=hgr_tiles[tile]
        for r in range(8):
            page[(out_row*8+r)*40+col]=b[r]
    return page

# get nametable from a2_art
import importlib
art=importlib.import_module('a2_art')
nt=art.nametable() if hasattr(art,'nametable') else None

def render_page(page, bitfirst, path):
    im=Image.new('RGB',(280,192)); px=im.load()
    for y in range(192):
        addr=0x2000+(y%8)*0x400+((y//8)%8)*0x80+(y//64)*0x28
        for byte in range(40):
            b=page[y*40+byte]
            for k in range(7):
                if (b>>((6-k) if bitfirst else k))&1:
                    px[byte*7+k,y]=(187,54,255) if (b&0x80) else (67,200,0)
    im.save(path)

results=[]
for rev in (False,True):
    rows=chr_rows(blob,rev)
    for rowsel in ('p','7p'):
        for bitfirst in (True,False):
            hgr=tile_to_hgr(rows,rowsel,bitfirst)
            page=build_page(hgr,nt)
            name='c%d%s%s' % (1 if rev else 0, 'a' if rowsel=='p' else 'b', '6' if bitfirst else '0')
            render_page(page,bitfirst,r'build\a2\combo_%s.png'%name)
            results.append(name)
            print('rendered', name)
print('DONE', results)
