"""Build a bootable DOS 3.3 master image (tracks 0-2 from dos33_system.bin) for
keyboard-injection tests.  Nothing is catalogued, so it boots to the "]" prompt.
"""
import sys

src = r'C:\dev\pom2games\dev\tools\dos33_system.bin'
out = sys.argv[1] if len(sys.argv) > 1 else r'build\a2\master.dsk'

sys3 = open(src, 'rb').read()
if len(sys3) != 12288:
    sys.exit('unexpected system image size %d' % len(sys3))
img = bytearray(35 * 16 * 256)
img[:12288] = sys3
open(out, 'wb').write(img)
print('wrote %s (%d bytes, 35 tracks)' % (out, len(img)))
