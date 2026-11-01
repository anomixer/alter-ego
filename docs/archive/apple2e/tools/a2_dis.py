"""Linear-sweep 6502 disassembler walk over the built images.

Every investigation this session has been bitten by reading instruction bytes at an
assumed start address.  This walks a program from a real entry point using derived
6502 instruction sizes, so every instruction boundary - and therefore every branch
target - is computed, not eyeballed.

Sizes are derived from the standard 6502 opcode layout: opcode >> 5 selects the
addressing family, and the index within the family fixes the size.  A wrong size is
exactly how this session kept landing mid-instruction.
"""
import sys


def _sizes():
    # Per family (opcode >> 5), size for index 0..31.  0 = not a valid 6502 opcode.
    # Written out family by family: the load/store families (0x80-0x9F, 0xA0-0xBF)
    # do NOT follow the arithmetic families' pattern, and assuming they do is what
    # makes a sweep land mid-instruction.
    fam = [
        # 0x00 BRK/ora:  0x0A = asl a (1), 0x0C = bit zp (2)
        [1, 2, 0, 3, 2, 2, 3, 3, 1, 2, 1, 0, 2, 3, 0, 3, 2, 2, 0, 3, 2, 2, 3, 3, 1, 2, 2, 0, 3, 3, 3, 3],
        # 0x20 jsr/and:  0x2A = rol a (1), 0x2C = bit abs (3)
        [3, 2, 0, 3, 2, 2, 3, 3, 1, 2, 1, 0, 3, 3, 0, 3, 2, 2, 0, 3, 2, 2, 3, 3, 1, 2, 2, 0, 3, 3, 3, 3],
        # 0x40 rti/eor:  0x4A = lsr a (1), 0x4C = jmp abs (3)
        [1, 2, 0, 3, 2, 2, 3, 3, 1, 2, 1, 0, 3, 3, 0, 3, 2, 2, 0, 3, 2, 2, 3, 3, 1, 2, 2, 0, 3, 3, 3, 3],
        # 0x60 rts/adc:  0x68 = pla (1), 0x6A = ror a (1), 0x6C = jmp (abs) (3)
        [1, 2, 0, 3, 2, 2, 3, 3, 1, 2, 1, 0, 3, 3, 0, 3, 2, 2, 0, 3, 2, 2, 3, 3, 1, 2, 2, 0, 3, 3, 3, 3],
        # 0x80 sty/lda/ldx:  0x82 = sta imm (2, 65C02), 0x8C sty abs, 0x8D lda abs,
        #                     0x91 lda (zp),y, 0x99 lda abs,y, 0x9D lda abs,x
        [3, 2, 2, 3, 2, 2, 2, 2, 1, 2, 1, 0, 3, 3, 3, 2, 2, 2, 0, 3, 2, 2, 2, 2, 1, 3, 1, 0, 3, 3, 3, 2],
        # 0xA0 ldy/lda:  0xA0 = ldy imm (2), 0xAC = ldy abs (3)
        [2, 2, 2, 3, 2, 2, 2, 2, 1, 2, 1, 0, 3, 3, 3, 2, 2, 2, 0, 3, 2, 2, 2, 2, 1, 3, 1, 0, 3, 3, 3, 2],
        # 0xC0 cpy/cmp/cpx:  0xC0 = cpy imm (2), 0xCC = cpy abs (3)
        [2, 2, 2, 3, 2, 2, 2, 2, 1, 2, 1, 0, 3, 3, 3, 2, 2, 2, 0, 3, 2, 2, 2, 2, 1, 3, 1, 0, 3, 3, 3, 2],
        # 0xE0 cpx/sbc/inc:  0xE0 = cpx imm (2), 0xEC = cpx abs (3)
        [2, 2, 2, 3, 2, 2, 2, 2, 1, 2, 1, 0, 3, 3, 3, 2, 2, 2, 0, 3, 2, 2, 2, 2, 1, 3, 1, 0, 3, 3, 3, 2],
    ]
    sz = {}
    for f in range(8):
        for i in range(32):
            s = fam[f][i]
            if s:
                sz[(f << 5) | i] = s
    # Branches are 2 bytes; the families above already list them as 2.
    # Documented 6502 NOPs, by size.
    for op, s in ((0x02, 1), (0x04, 1), (0x07, 1), (0x0A, 1), (0x0B, 1), (0x14, 2),
                  (0x1A, 1), (0x1C, 3), (0x34, 2), (0x3A, 1), (0x44, 2), (0x54, 2),
                  (0x74, 2), (0xD4, 2), (0xF4, 2), (0xEA, 1), (0x42, 1), (0x12, 1)):
        sz[op] = s
    return sz


SZ = _sizes()

MN = {0x20: 'jsr', 0x4C: 'jmp', 0x6C: 'jmp (', 0x60: 'rts', 0x40: 'rti', 0x00: 'brk',
      0xA9: 'lda #', 0xAD: 'lda abs', 0xA5: 'lda zp', 0xB1: 'lda (zp),y', 0x91: 'sta (zp),y',
      0x85: 'sta zp', 0x8D: 'sta abs', 0x8A: 'txa', 0x98: 'tya', 0xAA: 'tax', 0xA8: 'tay',
      0x88: 'dey', 0xC8: 'iny', 0xCA: 'dex', 0xE8: 'inx', 0x18: 'clc', 0x38: 'sec',
      0x69: 'adc #', 0x65: 'adc zp', 0xE9: 'sbc #', 0x0A: 'asl a', 0x09: 'ora #',
      0x29: 'and #', 0xC9: 'cmp #', 0xD0: 'bne', 0xF0: 'beq', 0x90: 'bcc', 0xB0: 'bcs',
      0x10: 'bpl', 0x30: 'bmi', 0x50: 'bvc', 0x70: 'bvs', 0x48: 'pha', 0x68: 'pla',
      0xA0: 'ldy #', 0xA2: 'ldx #', 0xE6: 'inc zp', 0xEE: 'inc abs', 0xCE: 'dec abs',
      0xA6: 'ldx zp', 0xAC: 'ldx abs', 0xB5: 'lda zp,x', 0x95: 'sta zp,x', 0x2D: 'and abs',
      0x2C: 'bit abs', 0x24: 'bit zp', 0x3A: 'dec a', 0x1A: 'inc a', 0xDE: 'ror abs,x',
      0x9D: 'sta abs,x', 0xBD: 'lda abs,x', 0x99: 'sta abs,y', 0xB9: 'lda abs,y',
      0x9C: 'stz abs', 0x0E: 'asl abs', 0x4E: 'lsr abs', 0x6E: 'ror abs', 0x2E: 'rol abs',
      0x86: 'stx zp', 0x84: 'sty zp', 0x26: 'stx zp', 0x25: 'and zp', 0x35: 'and zp,x',
      0x05: 'ora zp', 0x15: 'ora zp,x', 0x55: 'eor zp,x', 0x45: 'eor zp', 0xEA: 'nop',
      0x18: 'clc', 0xB8: 'clv', 0x58: 'cli', 0x78: 'sei', 0xD8: 'cld', 0xB8: 'clv',
      0xBA: 'tsx', 0x9A: 'txs', 0x6A: 'ror a', 0x2A: 'rol a', 0x4A: 'lsr a',
      0x08: 'php', 0x04: 'nop zp', 0x44: 'nop zp', 0x54: 'nop zp', 0x64: 'nop zp',
      0x74: 'nop zp,x', 0xD4: 'nop abs', 0xF4: 'nop abs', 0x1C: 'nop abs', 0x02: 'nop #',
      0x07: 'nop zp', 0x0B: 'nop imp', 0x14: 'nop zp', 0x34: 'nop zp', 0x12: 'nop imp'}


def walk(data, base, start, count):
    """Disassemble `count` instructions from `start`, following real 6502 sizes."""
    pc = start
    out = []
    for _ in range(count):
        off = pc - base
        if off < 0 or off + 3 > len(data):
            out.append((pc, '??', 0, ''))
            break
        op = data[off]
        size = SZ.get(op)
        if size is None:
            out.append((pc, 'INVALID $%02X' % op, 1, ''))
            pc = (pc + 1) & 0xFFFF
            continue
        extra = ''
        if op in (0x20, 0x4C):
            extra = '$%04X' % (data[off + 1] | (data[off + 2] << 8))
        elif op in (0x6C,):
            extra = '($%04X)' % (data[off + 1] | (data[off + 2] << 8))
        elif op in (0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0):
            d = data[off + 1]
            d = d - 256 if d > 127 else d
            extra = '$%04X' % ((pc + 2 + d) & 0xFFFF)
        elif size == 2:
            extra = '$%02X' % data[off + 1]
        elif size == 3:
            extra = '$%04X' % (data[off + 1] | (data[off + 2] << 8))
        elif size == 4:
            extra = '$%02X,$%04X' % (data[off + 1], data[off + 2] | (data[off + 3] << 8))
        out.append((pc, MN.get(op, '$%02X' % op), size, extra))
        pc = (pc + size) & 0xFFFF
    return out


if __name__ == '__main__':
    which = sys.argv[1]
    start = int(sys.argv[2], 16)
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    if which == 'game':
        data, base = open('build/a2/game.bin', 'rb').read(), 0x6000
    elif which == 'cold':
        data, base = open('build/a2/cold.bin', 'rb').read(), 0xD000
    else:
        raise SystemExit('game|cold')
    for pc, mn, size, extra in walk(data, base, start, n):
        print('$%04X: %-13s %s' % (pc, mn, extra))
