blob = open(r'src\tileset.chr', 'rb').read()
for t in range(2):
    print("tile", t)
    for r in range(8):
        lo = blob[t*16 + r*2]
        hi = blob[t*16 + r*2 + 1]
        row = []
        for p in range(8):
            v = ((hi >> (7-p)) & 1) << 1 | ((lo >> (7-p)) & 1)
            row.append(v)
        print(" ", row)
