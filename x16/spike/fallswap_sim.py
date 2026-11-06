"""Offline check for the X16 mid-air exchange (2026-11-06).

The report was "swapping while falling sometimes drops the Ego through the
platform".  This script rebuilds the exact geometry from the packed level
files and replays the fall/exchange code paths from vera/src/a2vera/main.c:

  * before the fix, a mid-air swap keeps `player_fall_steps`, so the fall
    resumes in the mirrored column without re-checking the floor.  When the
    mirrored column has a solid tile in the row the fall resumes into, the Ego
    ends up *inside* that tile; the next gravity test only looks one tile below
    and therefore keeps falling straight through the platform.
  * after the fix the swap snaps y back to the tile row and clears the fall
    steps, so gravity re-tests the mirrored column first.

Usage:
    python x16/spike/fallswap_sim.py            # report both variants
    python x16/spike/fallswap_sim.py --level 24
"""
import argparse
import os

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dist')

WALL, LADDER, BRIDGE = 0x01, 0x02, 0x10
FLOOR = WALL | LADDER | BRIDGE


def load_level(path):
    data = open(path, 'rb').read()
    pos = 2 + (data[0] | (data[1] << 8))   # RLE tilemap
    pos += 512 + 64                        # palettes
    count, pos = data[pos], pos + 1
    player = None
    for _ in range(count):
        typ, x, y = data[pos], data[pos + 1], data[pos + 2]
        pos += 3
        if typ == 0x20:
            player = (x << 3, y << 3)
    params = data[pos:pos + 3]
    collision = data[pos + 3:pos + 3 + 640]
    assert len(collision) == 640, (path, len(collision))
    return {'collision': collision, 'player': player,
            'exchanges': params[0], 'sync': params[1]}


class Map:
    def __init__(self, level):
        self.map = level['collision']
        self.sync = level['sync']

    def check(self, x, y):
        if x > 248 or y < 48 or y >= 208:
            return WALL
        return self.map[((y - 48) >> 3) * 32 + (x >> 3)]

    def alter(self, x, y):
        if not self.sync:
            return min(max(248 - x, 16), 240), y
        return x, min(max(240 - y, 48), 208)


def simulate(m, x, y0, t, fix, max_frames=400, level_sync=0):
    """Start mid-fall: t pixels into an eight-pixel step from the tile row y0."""
    y = y0 + t
    steps = (8 - t) % 8
    exchange = 0
    ex = ey = 0
    ax, ay = m.alter(x, y)
    if m.check(ax, ay) & WALL:
        return False, None, (x, y)    # exchange refused: no swap happens
    if fix and level_sync and not (m.check(ax, (ay + 8)) & FLOOR):
        return False, None, (x, y)    # ae_midair_ok(): no landing spot yet
    ex, ey = ax, ay
    exchange = 1
    clip = None
    for _ in range(max_frames):
        if exchange:
            for axis in ('x', 'y'):
                cur = x if axis == 'x' else y
                dst = ex if axis == 'x' else ey
                if cur < dst:
                    cur += min(4, dst - cur)
                elif cur > dst:
                    cur -= min(4, cur - dst)
                if axis == 'x':
                    x = cur
                else:
                    y = cur
            if x == ex and y == ey:
                exchange = 0
                if fix:
                    y &= 0xF8
                    steps = 0
        elif steps:
            y += 1
            steps -= 1
        else:
            here = m.check(x, y)
            below = m.check(x, y + 8)
            if not (here & LADDER) and not (below & FLOOR):
                y += 1
                steps = 7
            else:
                return clip is not None, clip, (x, y)
        if not exchange and 48 <= y < 208 and (m.check(x, y) & WALL):
            clip = (x, y)
            return True, clip, (x, y)
        if y >= 208:
            return clip is not None, clip, (x, y)
    return clip is not None, clip, (x, y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--level', type=int, default=-1)
    args = ap.parse_args()
    levels = [args.level] if args.level >= 0 else range(26)
    for fix in (False, True):
        total = bad = 0
        examples = []
        for lv in levels:
            path = os.path.join(DIST, 'LV%02d' % lv)
            if not os.path.exists(path):
                continue
            level = load_level(path)
            m = Map(level)
            if not level['exchanges']:
                continue
            for x in range(8, 249, 8):
                for y0 in range(48, 208, 8):
                    # the Ego must be falling here: no floor below
                    if m.check(x, y0 + 8) & FLOOR:
                        continue
                    ax, ay = m.alter(x, y0)
                    if m.check(ax, ay) & WALL:
                        continue
                    for t in range(1, 8):
                        total += 1
                        hit, where, _end = simulate(m, x, y0, t, fix, level_sync=level['sync'])
                        if hit:
                            bad += 1
                            if len(examples) < 6:
                                examples.append((lv, x, y0, t, ax, where))
        print('fix=%-5s scenarios=%5d clipped=%4d' % (fix, total, bad))
        for e in examples:
            print('   level %02d fall x=%3d y0=%3d press+%d -> mirror x=%3d clip %s'
                  % e)


if __name__ == '__main__':
    main()
