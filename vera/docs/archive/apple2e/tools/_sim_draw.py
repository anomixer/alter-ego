import sys, os
sys.path.insert(0, r'C:\dev\alter-ego\tools')
import a2_assets as A

# Read the DHGR title art RLE
stream = open(r'C:\dev\alter-ego\build\art\titledh.bin', 'rb').read()
print('stream len', len(stream), 'tag', hex(stream[0]))

# 1) Reference decode (should be the 15360-byte buffer)
buf = A.decode_rle(stream)
print('reference decode len', len(buf))

# 2) Simulate the ASSEMBLY dhgr_draw_screen EXACTLY.
#    put_byte: write byte to (line_idx, slot_idx), addr = row_ptr + (slot_idx>>1),
#    even slot -> aux, odd slot -> main.  Row ptr from dhgr_line_off (HGR row table).
def hgr_row(y):
    return 0x2000 + (y%8)*1024 + ((y//8)%8)*128 + (y//64)*40

# Build the logical 80-slot lines by placing each decoded byte
lines = [bytearray(80) for _ in range(192)]
# The assembly reads the RLE stream and places bytes sequentially into slot order.
# The buffer (buf) IS slot order, so lines[y][slot] = buf[y*80+slot].  But let's
# also simulate the assembly decode to double-check it matches buf.
slot = 0
line = 0
def put(b):
    global slot, line
    lines[line][slot] = b
    slot += 1
    if slot == 80:
        slot = 0
        line += 1

# assembly decode
tag = stream[0]
i = 1
last = 0
nbytes = 0
while True:
    b = stream[i]; i += 1
    if b != tag:
        put(b); last = b; nbytes += 1
        continue
    n = stream[i]; i += 1
    if n == 0:
        break
    for _ in range(n):
        put(last); nbytes += 1
print('assembly sim decoded bytes', nbytes, '(expect 15360)')

# 3) Convert logical lines -> (main, aux) banks via dhgr_slot
def dhgr_slot(byte):
    return (byte >> 1, (byte & 1) ^ 1)  # even->aux
main = bytearray(192*40)
aux  = bytearray(192*40)
for y in range(192):
    for b in range(80):
        off, is_aux = dhgr_slot(b)
        if is_aux: aux[y*40+off] = lines[y][b]
        else:      main[y*40+off] = lines[y][b]

# 4) Render
A.save_png(bytes(main), bytes(aux), r'C:\dev\alter-ego\build\a2\sim_draw.png')
print('wrote sim_draw.png')

# Also render the reference decode directly (should match)
# And count nonzero
nz = sum(1 for ln in lines for b in ln if b)
print('nonzero slots', nz, 'of', 192*80)
