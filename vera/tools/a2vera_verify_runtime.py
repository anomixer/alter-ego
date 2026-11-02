"""Assert state and VRAM from actual AppleWin runs against converted NES data."""
import argparse
import re
from pathlib import Path
from a2vera_snapshot import read_snapshot, symbols

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT/'vera/build'


def verify_level(snapshot, level):
    text, ram, vram, _ = read_snapshot(snapshot)
    sym = symbols(BUILD/'game.dbg')
    value = lambda name: ram[sym['_'+name]]
    assert value('current_level') == level, (level, value('current_level'))
    assert value('paused') == 1, 'Game did not accept pause'
    assert value('start_delay') == 0, 'Level is still in its intro'
    assert value('player_dead') == 0, 'Player died before pause'
    assert value('items_left') <= 20
    assets = BUILD/'levels'/f'LV{level:02}'
    assert value('exchange_left') == (assets/'level_params.bin').read_bytes()[0]
    assert vram[0x10000:0x12000] == (BUILD/'title_tiles_4bpp.bin').read_bytes()
    assert vram[0x12000:0x14000] == (BUILD/'title_tiles_alt_4bpp.bin').read_bytes()
    assert not any(vram[0x1FE00:0x20000]), 'Unused hardware sprites were not cleared'
    expected = (assets/'title_map.bin').read_bytes()
    collision = (assets/'level_collision.bin').read_bytes()
    ignored = set()
    for cell, tile_type in enumerate(collision):
        if tile_type & 12:
            row, col = divmod(cell, 32)
            ignored.add(((row+6)*64+col+4)*2)
            ignored.add(((row+6)*64+col+4)*2+1)
    diffs = [i for i, (a,b) in enumerate(zip(vram[:4096], expected))
             if a != b and i not in ignored]
    assert not diffs, f'Level map differs at {diffs[:10]}'
    mapping = (BUILD/'level1.map').read_text()
    base = int(re.search(r'^CODE\s+([\dA-F]+)', mapping, re.M)[1], 16)
    size = int(re.search(r'main.o:\s+CODE\s+Offs=[\dA-F]+\s+Size=([\dA-F]+)', mapping)[1], 16)
    image = (BUILD/'AE2VERA#062000').read_bytes()
    assert ram[base:base+size] == image[base-0x2000:base-0x2000+size], 'Game code was overwritten'
    assert all(vram[0x1F9C0+i] == 0 for i in (2,6,10,14)), 'Pause did not mute music'
    dim=(assets/'level_pause_palette.bin').read_bytes()
    for bank in range(8):
        assert vram[0x1FA00+bank*32:0x1FA08+bank*32] == dim[bank*8:bank*8+8], 'Pause palette differs'
    print(f'PASS LV{level:02}: map, tiles, code, sprites, pause; '
          f'items={value("items_left")}, reserves={value("lives_remaining")}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('snapshot')
    p.add_argument('--level', type=int, required=True)
    args = p.parse_args()
    verify_level(args.snapshot, args.level)
