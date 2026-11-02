#!/usr/bin/env python3
"""Compile original FamiTone APU-register effects into VERA PSG frame data."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NES_CLOCK = 1_789_772.727272727
VERA_CLOCK = 25_000_000 / 512
NOISE_PERIOD = (4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068)
SFX_NOISE_MAX_HZ = 8000


def parse_source():
    text = (ROOT / "src/sounds.s").read_text(encoding="utf-8")
    table = re.search(r"^sounds:\s*$", text, re.M)
    names = re.findall(r"^\s*\.word\s+(@sfx\d+)\s*$", text[table.end():], re.M)
    sounds = []
    for name in names:
        body = re.search(r"^" + re.escape(name) + r":\s*$", text, re.M)
        data = []
        for line in text[body.end():].splitlines():
            line = line.strip()
            if not line:
                continue
            if not line.startswith(".byte"):
                break
            data.extend(int(x.strip().replace("$", "0x"), 0) for x in line[5:].split(","))
        sounds.append((name, data))
    return sounds


def phase(hz):
    return max(0, min(0xFFFF, round(hz * 131072 / VERA_CLOCK)))


def compile_effect(data):
    regs = [0] * 11
    off = repeat = 0
    frames = []
    ended = False
    for _ in range(180):
        if repeat:
            repeat -= 1
        else:
            while off < len(data):
                op = data[off]
                off += 1
                if op < 0x10:
                    regs[op] = data[off]
                    off += 1
                    continue
                if op == 0xFF:
                    ended = True
                    break
                repeat = op - 0x10
                break

        frame = bytearray()
        for channel in range(4):
            base = channel * 3
            vol = regs[base] & 0x0F if channel < 3 else regs[9] & 0x0F
            if channel < 2:
                timer = ((regs[base + 2] & 7) << 8) | regs[base + 1]
                hz = NES_CLOCK / (16 * (timer + 1)) if vol and timer < 0x7F8 else 0
                wave = 0x3F
            elif channel == 2:
                timer = ((regs[8] & 7) << 8) | regs[7]
                hz = NES_CLOCK / (32 * (timer + 1)) if regs[6] and timer < 0x7F8 else 0
                vol = min(vol, 15) if hz else 0
                wave = 0x80
            else:
                idx = regs[10] & 0x0F
                hz = NES_CLOCK / NOISE_PERIOD[idx] if vol else 0
                wave = 0xC0
            p = phase(hz) if vol else 0
            gain = round(vol * 63 / 15) if vol else 0
            frame.extend((p & 255, p >> 8, (0xC0 | gain) if gain else 0, wave))
        frames.append(bytes(frame))
        if ended:
            break
    else:
        raise ValueError("effect exceeds 180 frames")
    if not ended:
        raise ValueError("effect has no terminator")
    return frames


def main():
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "vera/build/ftm_sfx_data.s"
    sounds = parse_source()
    periods = set()
    for _, data in sounds:
        regs, off = [0] * 11, 0
        while off < len(data):
            op = data[off]
            off += 1
            if op < 0x10:
                regs[op] = data[off]
                off += 1
                if op in (1, 2): periods.add(((regs[2] & 7) << 8) | regs[1])
                if op in (4, 5): periods.add(((regs[5] & 7) << 8) | regs[4])
                if op in (7, 8): periods.add(((regs[8] & 7) << 8) | regs[7])
            elif op == 0xFF:
                break
    # Music and game link separately. Derive the game's absolute SFX addresses
    # from the music overlay config so the two link targets stay in sync.
    config = (ROOT / "vera/src/a2vera/music_ftm.cfg").read_text(encoding="ascii")
    match = re.search(r"SFXDATA:\s*load\s*=\s*RAM,\s*type\s*=\s*ro,\s*start\s*=\s*\$([0-9a-fA-F]+)", config)
    if not match:
        raise ValueError("SFXDATA start missing from music_ftm.cfg")
    data_base = int(match.group(1), 16)
    period_base = data_base + 2 * len(sounds)
    noise_base = period_base + 4 * len(periods)
    tables_header = output.parent / "ftm_tables.h"
    with tables_header.open("a", encoding="ascii", newline="\n") as f:
        f.write(f"#define FTM_NOISE_PHASE_TABLE ((const unsigned int*)0x{noise_base:04X}u)\n")
    (output.parent / "ftm_sfx_layout.inc").write_text(
        f"FTM_SFX_TABLE = ${data_base:04X}\n"
        f"FTM_SFX_PERIOD_TABLE = ${period_base:04X}\n"
        f"FTM_SFX_PERIOD_COUNT = {len(periods)}\n"
        f"FTM_SFX_NOISE_TABLE = ${noise_base:04X}\n",
        encoding="ascii", newline="\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="ascii", newline="\n") as f:
        f.write('; Generated from src/sounds.s by vera/tools/a2vera_ftm_sfx.py.\n')
        f.write('.setcpu "6502"\n.segment "SFXDATA"\n.export _ftm_sfx_table, _ftm_sfx_periods, _ftm_sfx_noises\n_ftm_sfx_table:\n')
        for i in range(len(sounds)): f.write(f'    .word ftm_sfx_{i}\n')
        f.write('_ftm_sfx_periods:\n')
        for p in sorted(periods):
            f.write(f'    .word ${p:04X},${phase(NES_CLOCK/(16*(p+1))):04X}\n')
        f.write('_ftm_sfx_noises:\n')
        f.write('    .word ' + ','.join(
            f'${phase(min(NES_CLOCK/p, SFX_NOISE_MAX_HZ)):04X}'
            for p in NOISE_PERIOD) + '\n')
        for i, (name, data) in enumerate(sounds):
            f.write(f'ftm_sfx_{i}: ; {name}\n')
            for j in range(0, len(data), 12):
                f.write('    .byte ' + ','.join(f'${b:02X}' for b in data[j:j+12]) + '\n')
    print(f"generated {output}: {len(sounds)} original effects, {len(periods)} timers, {sum(map(lambda x: len(x[1]), sounds))+2*len(sounds)+4*len(periods)+32}B")


if __name__ == "__main__":
    main()
