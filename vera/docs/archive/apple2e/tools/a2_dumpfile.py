"""Dump a file's stored bytes from a DOS 3.3 image, so the on-disk form of a
type-A (ASCII) file can be compared with the source that was packed."""
import sys
sys.path.insert(0, r'C:\dev\pom2games\dev\tools')
import dos33

img = sys.argv[1]
name = sys.argv[2].upper()

d = dos33.Dos33(img) if hasattr(dos33, 'Dos33') else None
if d is None:
    # fall back to the module's documented helpers
    print('module API:', [n for n in dir(dos33) if not n.startswith('_')])
    sys.exit(0)
