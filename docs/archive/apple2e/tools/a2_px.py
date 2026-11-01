from PIL import Image
import numpy as np
a = np.array(Image.open(r'build\a2\emu_t10.png').convert('RGB'))
b = np.array(Image.open(r'build\a2\off_bit0.png').convert('RGB'))
# glyph shape = non-black pixels
ga = (a.sum(axis=2) > 0)
gb = (b.sum(axis=2) > 0)
diff = ga ^ gb
print("emu_t9 glyph px:", ga.sum(), "off_bit0 glyph px:", gb.sum())
print("differing glyph px:", diff.sum(), "of", ga.sum())
# where do they differ (sample)
ys, xs = np.where(diff)
if len(xs):
    print("first diffs (x,y):", list(zip(xs[:10], ys[:10])))
    print("x range of diffs:", xs.min(), xs.max(), " y range:", ys.min(), ys.max())
