"""Make the Apple II assembly portable to a plain NMOS 6502 target.

cc65's apple2enh target assembles for the //e's 65C02, so BRA is legal there.
The plain `apple2` target is strict NMOS 6502, where BRA does not exist -- and
the a2run emulator core is a NMOS 6502 (an Apple II+), so a 65C02 opcode there
is an illegal instruction.

BRA is only a 2-byte forward branch, so replacing it with JMP keeps identical
semantics on every 6502 and lets the same sources build for both targets.

Also give tick_frame()'s II/II+ delay loop its two zero-page counters: sys.s
declares its RAM in the BSS segment (there is no ZEROPAGE segment in this file).
"""
import io
import re

files = [r'C:\dev\alter-ego\src\a2\sys.s',
         r'C:\dev\alter-ego\src\a2\hgr.s',
         r'C:\dev\alter-ego\src\a2\dhgr.s']

for p in files:
    s = io.open(p, encoding='utf-8').read()
    n = len(re.findall(r'\bbra\s', s))
    s = re.sub(r'\bbra(\s+)', r'jmp\1', s)
    io.open(p, 'w', encoding='utf-8').write(s)
    print('%-28s bra -> jmp: %d' % (p.rsplit('\\', 1)[-1], n))

# tick_frame() delay counters, in the segment sys.s already uses for RAM
p = r'C:\dev\alter-ego\src\a2\sys.s'
s = io.open(p, encoding='utf-8').read()
if 'frame_lo' not in s:
    m = re.search(r'(\.segment "BSS"\s*\nlast_key:\s*\n\s*\.res\s+1\s*\n)', s)
    if not m:
        raise SystemExit('sys.s BSS anchor not found')
    s = s[:m.end()] + '\nframe_lo: .res 1\nframe_hi: .res 1\n' + s[m.end():]
    io.open(p, 'w', encoding='utf-8').write(s)
    print('added frame_lo/frame_hi to sys.s BSS')
else:
    print('frame_lo already present')
