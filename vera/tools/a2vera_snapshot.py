"""Read AppleWin snapshots without losing the second 64 KB of VERA VRAM."""
import argparse
import re
from pathlib import Path


def memory_section(text):
    out = bytearray()
    for _, data in re.findall(r'^\s+([\dA-F]{4}): ([\dA-F]+)\s*$', text, re.M):
        out.extend(bytes.fromhex(data))
    return out


def read_snapshot(path):
    text = Path(path).read_text(encoding='utf-8')
    main = memory_section(text.split('    Main Memory:\n', 1)[1].split('\nUnit:', 1)[0])[:65536]
    vera = text.split('      Card: VERA\n', 1)[1]
    vram = memory_section(vera.split('        Video RAM:\n', 1)[1].split('          Registers:', 1)[0])
    assert len(vram) == 131072, len(vram)
    registers = memory_section(vera.split('          Registers:\n', 1)[1].split('      Card:', 1)[0])
    return text, main, vram, registers


def symbols(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        if not line.startswith('sym\t'):
            continue
        name = re.search(r'name="([^"]+)"', line)
        val = re.search(r'val=0x([\dA-Fa-f]+)', line)
        if name and val:
            result[name[1]] = int(val[1], 16)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('snapshot')
    p.add_argument('--dump-prefix')
    p.add_argument('--symbols')
    p.add_argument('--expect',action='append',default=[])
    args = p.parse_args()
    text, main, vram, registers = read_snapshot(args.snapshot)
    pc = int(re.search(r'      PC: 0x([\dA-F]+)', text)[1], 16)
    sp = int(re.search(r'      S: 0x([\dA-F]+)', text)[1], 16)
    print(f'PC=${pc:04X}, S=${sp:02X}, hardware stack={main[0x101+sp:0x200].hex()}')
    print(f'Code at PC: {main[pc:pc+16].hex()}')
    print(f'VRAM={len(vram)}, registers={len(registers)}')
    print('PSG:', vram[0x1F9C0:0x1F9D4].hex())
    if args.symbols:
        sym = symbols(args.symbols)
        for name in ('current_level','lives_remaining','player_x','player_y',
                     'items_left','exchange_left','paused','player_dead',
                     'start_delay','level_clear_timer','level_cleared','level_skip',
                     'player_move_steps','player_fall_steps','frame_count'):
            print(f'{name}: {main[sym["_"+name]]}')
        for item in args.expect:
            name,wanted=item.split('=',1)
            actual=main[sym['_'+name]]
            assert actual==int(wanted,0), f'{name}: expected {wanted}, got {actual}'
    if args.dump_prefix:
        Path(args.dump_prefix+'.ram').write_bytes(main)
        Path(args.dump_prefix+'.vram').write_bytes(vram)
