#!/usr/bin/env python3
"""Convert a FamiTone2 effect to a one-shot VERA PSG frame stream.

The output is four VERA voice-4 register values per frame, followed by four
$FF bytes. Fixed records keep the 6502 player small and stream-safe.
"""
import re
import sys
from pathlib import Path

NES_CLOCK = 1789773.0
VERA_CLOCK = 25000000.0 / 512.0
NES_NOISE_PERIODS = (4, 8, 16, 32, 64, 96, 128, 160,
                     202, 254, 380, 508, 762, 1016, 2034, 4068)


def parse_effect(text, index):
    table = re.search(r"^sounds:\s*$", text, re.M)
    if not table:
        raise ValueError("missing sounds: pointer table")
    names = re.findall(r"^\s*\.word\s+(@sfx\d+)\s*$", text[table.end():], re.M)
    label = names[index]
    body = re.search(r"^" + re.escape(label) + r":\s*$", text, re.M)
    if not body:
        raise ValueError("missing effect " + label)
    data = []
    for line in text[body.end():].splitlines():
        line = line.strip()
        if not line:
            continue
        if not line.startswith(".byte"):
            break
        for token in line[5:].split(","):
            token = token.strip()
            data.append(int(token[1:], 16) if token.startswith("$") else int(token))
    return label, data


def main():
    if len(sys.argv) != 4:
        raise SystemExit("usage: famitone_sfx_to_vera_psg.py sounds.s effect-index out.psg")
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    effect_index = int(sys.argv[2])
    label, data = parse_effect(text, effect_index)
    off = repeat = 0
    regs = [0] * 11
    events = []
    ended = False
    for frame in range(180):
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
        # FamiTone register groups are pulse 1 (0..2), pulse 2 (3..5),
        # triangle (6..8), noise (9..10). Pick the loudest active source;
        # many original effects deliberately write more than one APU voice.
        candidates = []
        for base in (0, 3):
            vol = regs[base] & 0x0F
            timer = ((regs[base + 2] & 7) << 8) | regs[base + 1]
            if vol and timer < 0x7F8:
                candidates.append((vol, timer, 0x20))
        vol = regs[6] & 0x0F
        timer = ((regs[8] & 7) << 8) | regs[7]
        if vol and timer < 0x7F8:
            candidates.append((vol, timer, 0x80))
        noise_vol = regs[9] & 0x0F
        noise_period = regs[10] & 0x0F
        if noise_vol:
            # NES APU noise periods are discrete. VERA's noise clock is
            # represented by its frequency register and noise waveform.
            noise_hz = NES_CLOCK / NES_NOISE_PERIODS[noise_period]
            candidates.append((noise_vol, noise_hz, 0xC0))
        if candidates:
            volume, source, wave = max(candidates, key=lambda item: item[0])
            if wave == 0xC0:
                hz = source
            elif wave == 0x80:
                hz = NES_CLOCK / (32.0 * (source + 1))
            else:
                hz = NES_CLOCK / (16.0 * (source + 1))
        else:
            volume, hz, wave = 0, 0, 0x20
        freq = max(0, min(0xFFFF, round(hz * 131072 / VERA_CLOCK)))
        # Triangle effect 9's source envelope is only volume 1. Give that
        # short cue enough level to remain audible after adapting it to VERA.
        if effect_index == 9:
            volume = min(15, volume * 3)
        vol = 0xC0 | min(63, round(volume * 61 / 15)) if volume else 0
        # Use PSG voice 4 (registers 16..19), leaving the music's four
        # converted NES voices untouched during the start transition.
        events.append(bytes([freq & 255, (freq >> 8) & 255, vol, wave]))
        if ended:
            break
    else:
        raise ValueError("effect did not terminate within 180 frames")
    # The source noise cues 11/12 contain just one active 60 Hz frame; on
    # VERA this is too brief to hear reliably. Sustain the noise for 4 frames.
    if effect_index in (11, 12) and events and events[0][2]:
        events[1:1] = [events[0]] * 3
    events.append(b"\xff\xff\xff\xff")
    Path(sys.argv[3]).write_bytes(b"".join(events))
    print(f"Wrote {sys.argv[3]}: {len(events)} frames ({len(events)/60:.2f} s), one-shot {label}")


if __name__ == "__main__":
    main()
