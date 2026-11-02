from pathlib import Path
import re,sys
import a2vera_title as V
ROOT=Path(__file__).resolve().parents[2]
LEVEL=int(sys.argv[1]) if len(sys.argv)>1 else 1
OUT=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/f'vera/build_level{LEVEL}'

def encode_map_rle(data):
 out=bytearray(); i=0
 while i<len(data):
  j=i+1
  while j<len(data) and data[j]==data[i] and j-i<130: j+=1
  if j-i>=3:
   out.extend((0x80|(j-i-3),data[i])); i=j
  else:
   start=i; i=j
   while i<len(data) and i-start<128:
    j=i+1
    while j<len(data) and data[j]==data[i] and j-i<3: j+=1
    if j-i>=3: break
    i=j
   n=i-start; out.append(n-1); out.extend(data[start:i])
 return out
raw=V.decode_rle(V.c_array(ROOT/f'src/map{LEVEL}.h'))
if len(raw)!=1024: raise ValueError(f'map{LEVEL} decoded to {len(raw)} bytes')
nt,attrs=raw[:960],raw[960:]
# NES game_add_background(): fixed metal frame and level-seeded star field.
# Read collision/entity markers from the original nametable, as the NES does.
visual_nt=bytearray(nt)
visual_nt[5*32+1:5*32+31]=bytes([1,2]+[3]*26+[4,1])
visual_nt[26*32+1:26*32+31]=bytes([1,8]+[9]*26+[10,1])
for row,tile in enumerate([5]+[6]*18+[7],6): visual_nt[row*32+1]=tile
for row,tile in enumerate([11]+[12]*18+[13],6): visual_nt[row*32+30]=tile
seed=(LEVEL+1)&255
def nes_rand():
 global seed
 seed=((seed<<1) ^ (0xCF if seed&0x80 else 0))&255
 return seed
star=nes_rand()&7
for row in range(20):
 for col in range(2,30):
  cell=(row&~1)*32+(col&~1)
  if not (nt[6*32+cell]|nt[6*32+cell+1]|nt[6*32+cell+32]|nt[6*32+cell+33]):
   if star<8: visual_nt[(row+6)*32+col]=0xB8+star
   star+=1+(nes_rand()&3)
   if star>30: star=0
chrdata=(ROOT/'src/tileset.chr').read_bytes()
tiles=bytearray(); alt_tiles=bytearray()
for t in range(256):
 for y in range(8):
  lo,hi=chrdata[t*16+y],chrdata[t*16+y+8]
  alo,ahi=chrdata[4096+t*16+y],chrdata[4096+t*16+y+8]
  for x in range(0,8,2):
   a=(((hi>>(7-x))&1)<<1)|((lo>>(7-x))&1)
   b=(((hi>>(6-x))&1)<<1)|((lo>>(6-x))&1)
   tiles.append(a*16+b)
  for x in range(0,8,2):
   a=(((ahi>>(7-x))&1)<<1)|((alo>>(7-x))&1)
   b=(((ahi>>(6-x))&1)<<1)|((alo>>(6-x))&1)
   alt_tiles.append(a*16+b)
mapdata=bytearray(64*32*2)
for y in range(30):
 for x in range(32):
  tile=visual_nt[y*32+x]; av=attrs[(y>>2)*8+(x>>2)]
  bank=(av>>(((y&2)<<1)|(x&2)))&3; o=(y*64+x+4)*2
  mapdata[o]=tile; mapdata[o+1]=bank<<4
# Turn NES entity markers into native VERA 8x8 hardware sprites.  One NES
# 8x16 character is represented by two vertically adjacent sprites, matching
# the game's OAM layout and keeping all 256 CHR tiles resident as sprite data.
sprites=bytearray(64*8)
sprite_count=0
player_xy=None
entities=bytearray()
for y in range(6,26):
 for x in range(32):
  tile=nt[y*32+x]
  if tile in (0x20,0x21,0x22,0x23,0x24):
   entities.extend((tile,x,y))
  if tile not in (0x20,0x21,0x22,0x23,0x24): continue
  if sprite_count+1>=64: raise ValueError('more than 31 two-part entities')
  if tile==0x20:
   player_xy=(x*8,y*8)
   upper,lower,pal=0x90,0xA0,5
  elif tile in (0x21,0x22):
   upper,lower,pal=0xB0,0xC0,6
  else:
   upper,lower,pal=0xB4,0xC4,6
  sx=32+x*8; sy=y*8-8
  for chrid,py in ((upper,sy),(lower,sy+8)):
   sprites[sprite_count*8:(sprite_count+1)*8]=bytes((
    (chrid+0x00)&255, 0x08, sx&255, (sx>>8)&3,
    py&255, (py>>8)&3, 0x0C, pal
   ))
   sprite_count+=1
# The dark Alter Ego is a second source-game character, synchronized to the
# active player rather than stored as a map marker. Mirror its initial position
# with the same level_params rule used in src/game.c.
params_text=(ROOT/'src/game.c').read_text(encoding='ascii')
params_text=params_text.split('const unsigned char level_params[26*2]={',1)[1].split('};',1)[0]
params_text=re.sub(r'//[^\n]*','',params_text)
params=[int(v) for v in re.findall(r'\b\d+\b',params_text)]
restart,sync=params[LEVEL*2:LEVEL*2+2]
if player_xy is not None:
 px,py=player_xy
 if sync==0:
  ax=max(16,min(240,248-px)); ay=py
 else:
  ax=px; ay=max(48,min(208,240-py))
 for chrid,sy in ((0x97,ay-8),(0xA7,ay)):
  sprites[sprite_count*8:(sprite_count+1)*8]=bytes((
   chrid,0x08,(32+ax)&255,((32+ax)>>8)&3,
   sy&255,(sy>>8)&3,0x0C,5
  ))
  sprite_count+=1
palnum=max(1,min((LEVEL-1)//5,4)+1)
ptext=(ROOT/'src/palettes.h').read_text(encoding='ascii')
m=re.search(r'palGameBG%d\[16\]\s*=\s*\{([^}]*)\}'%palnum,ptext)
if not m: raise ValueError(f'palGameBG{palnum} unavailable')
codes=[int(v,16) for v in re.findall(r'0x([\da-fA-F]{2})',m.group(1))]
if len(codes)!=16: raise ValueError('expected 16 palette entries')
palette=bytearray(512)
for bank in range(4):
 for shade in range(4):
  r,g,b=V.nes_rgb(codes[bank*4+shade]); i=bank*16+shade
  palette[i*2]=(g>>4)<<4|(b>>4); palette[i*2+1]=r>>4
spal=re.search(r'palSprites\[16\]\s*=\s*\{([^}]*)\}',ptext)
if not spal: raise ValueError('palSprites unavailable')
sprite_codes=[int(v,16) for v in re.findall(r'0x([\da-fA-F]{2})',spal.group(1))]
if len(sprite_codes)!=16: raise ValueError('expected 16 sprite palette entries')
sprite_codes[12:16]=codes[12:16]
# VERA sprite offset codes 4..7 refer to global palette bases 64..127.
for bank in range(4):
 for shade in range(4):
  r,g,b=V.nes_rgb(sprite_codes[bank*4+shade]); i=(4+bank)*16+shade
  palette[i*2]=(g>>4)<<4|(b>>4); palette[i*2+1]=r>>4
pause_palette=bytearray()
for bank in range(8):
 for shade in range(4):
  code=(codes if bank<4 else sprite_codes)[(bank&3)*4+shade]
  if bank not in (0,4):
   for _ in range(2):
    code=code-0x10 if code>=0x10 else 0x0F
    if not code: code=0x0F
  r,g,b=V.nes_rgb(code)
  pause_palette.extend(((g>>4)<<4|(b>>4),r>>4))
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'title_tiles_4bpp.bin').write_bytes(tiles)
(OUT/'title_tiles_alt_4bpp.bin').write_bytes(alt_tiles)
(OUT/'title_map.bin').write_bytes(mapdata)
(OUT/'level_map_rle.bin').write_bytes(encode_map_rle(mapdata))
(OUT/'level_map_size.bin').write_bytes(len(encode_map_rle(mapdata)).to_bytes(2,'little'))
(OUT/'level_palette.bin').write_bytes(palette)
(OUT/'level_pause_palette.bin').write_bytes(pause_palette)
(OUT/'level_sprites.bin').write_bytes(sprites)
(OUT/'level_entities.bin').write_bytes(bytes((len(entities)//3,))+entities)
(OUT/'level_params.bin').write_bytes(bytes((restart,sync,seed)))
# Logical collision map used by game.c: only the visible 20 rows are resident,
# and dynamic actors are converted to empty cells before collision checks.
gtext=(ROOT/'src/game.c').read_text(encoding='ascii')
macros={k:int(v,16) for k,v in re.findall(r'#define\s+(TILE_(?:EMPTY|WALL|LADDER|ITEM1|ITEM2|BRIDGE|WATER))\s+0x([\da-fA-F]+)',gtext)}
tmatch=re.search(r'const unsigned char tileType\[64\]\s*=\s*\{([^}]*)\}',gtext,re.S)
if not tmatch: raise ValueError('tileType table missing')
trefs=re.findall(r'TILE_(?:EMPTY|WALL|LADDER|ITEM1|ITEM2|BRIDGE|WATER)',tmatch.group(1))
if len(trefs)!=64: raise ValueError(f'tileType table has {len(trefs)} entries')
tile_types=[macros[t] for t in trefs]
collision=bytearray()
for tile in nt[6*32:26*32]:
 if tile in (0x20,0x21,0x22,0x23,0x24): tile=0
 collision.append(tile_types[tile])
(OUT/'level_collision.bin').write_bytes(collision)
from PIL import Image
im=Image.new('RGB',(320,240),(0,0,0)); px=im.load()
for y in range(30):
 for x in range(32):
  t=visual_nt[y*32+x]; av=attrs[(y>>2)*8+(x>>2)]; bank=(av>>(((y&2)<<1)|(x&2)))&3
  for ty in range(8):
   lo,hi=chrdata[t*16+ty],chrdata[t*16+ty+8]
   for tx in range(8):
    shade=(((hi>>(7-tx))&1)<<1)|((lo>>(7-tx))&1)
    px[32+x*8+tx,y*8+ty]=V.nes_rgb(codes[bank*4+shade])
im.save(OUT/f'level{LEVEL}_vera_preview.png')
print(f'level {LEVEL}: 960 tiles + attributes -> {len(mapdata)}B VERA map; tiles {len(tiles)}B, palette {len(palette)}B')
print(f'level {LEVEL}: {sprite_count//2} two-part entities -> {len(sprites)}B sprite attributes')
print(f'preview: {OUT/f"level{LEVEL}_vera_preview.png"}')
