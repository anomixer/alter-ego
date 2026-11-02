import sys
from collections import Counter
from PIL import Image

for p in sys.argv[1:]:
    im = Image.open(p).convert('RGB')
    w, h = im.size
    px = list(im.getdata())
    c = Counter(px)
    print('%s  %dx%d  distinct=%d' % (p.rsplit('\\', 1)[-1], w, h, len(c)))
    for col, n in c.most_common(6):
        print('    #%02X%02X%02X  %7d px  (%.1f%%)' % (col[0], col[1], col[2], n, 100.0 * n / (w * h)))
    # per-row ink coverage, to see whether the HGR field is actually painted
    ink = 0
    rows = []
    for y in range(h):
        n = sum(1 for x in range(w) if px[y * w + x] != (0, 0, 0))
        rows.append(n)
        ink += n
    band = [sum(rows[y * 16:(y + 1) * 16]) for y in range(0, h // 16)]
    print('    non-black total = %d' % ink)
    print('    ink per 16-row band: ' + ' '.join(str(b) for b in band[:24]))
