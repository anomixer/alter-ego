"""Compare the emulator's low RAM dumps against what the program should have
written, to tell whether neslib_init() ran and whether the art staging landed."""
import os

def load(nm):
    f = os.path.join(r'build\a2', nm)
    if not os.path.exists(f):
        return None
    return open(f, 'rb').read()

v = load('ae2_vram.bin')
if v:
    nz = sum(1 for b in v if b)
    print('vram shadow ($0800, %d bytes): %d nonzero' % (len(v), nz))
    print('   first 32:', v[:32].hex(' '))
    print('   all zero?', all(b == 0 for b in v))
else:
    print('ae2_vram.bin MISSING')

a = load('ae2_1000.bin')
c = open(r'build\art\credits.bin', 'rb').read()
if a:
    print('staging ($1000, %d bytes)' % len(a))
    print('   disk CREDITS first 16:', c[:16].hex(' '))
    print('   emul  $1000 first 16:', a[:16].hex(' '))
    print('   CREDITS stream present at $1000?', a[:len(c)] == c)
    print('   nonzero', sum(1 for b in a if b))
else:
    print('ae2_1000.bin MISSING')
