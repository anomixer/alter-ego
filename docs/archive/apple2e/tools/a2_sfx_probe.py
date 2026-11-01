#!/usr/bin/env python3
"""Offline AY/Mockingboard probe for the Apple II port.

a2run has no Mockingboard and this host has no sound card, so the AY driver in
src/a2/ftm.s has never been observed producing anything.  This simulates the
driver's own semantics - sfx_start, sfx_step, the four sfx_* converters,
mix_cand, and the R7 mixer - over the real src/sounds.s data, and prints the
AY register set per frame.  It is a faithful transcription of ftm.s, not a
model of famitone2: the effect encoding here is the port's own.

Effect buffer (stride SF_SIZE=15, data starts at SF_BUF=4):
  0 pulse1 duty      1 pulse1 volume   2 pulse1 period (8-bit fine)
  3 pulse2 duty      4 pulse2 volume   5 pulse2 period
  6 triangle gate    7 tri fine        8 tri coarse
  9 noise volume    10 noise period index
Stream record: 0 ptr_lo 1 ptr_hi 2 offset 3 repeat, then the 11-byte buffer.

sfx_step opcodes (ftm.s:906-952):
  $00-$0F  register write: opcode = buffer offset, next byte = value
  $10-$FE  hold the current setting for (byte - $10) frames
  $FF      end of effect
"""
import math
import re
import sys

SF_SIZE, SF_BUF, SF_REPEAT = 15, 4, 3
STREAMS = 4


def parse_sounds(path):
    """Return (order, {name: bytes}) from src/sounds.s."""
    text = open(path, "r", encoding="utf-8", errors="replace").read()
    m = re.search(r"^sounds:\s*$", text, re.M)
    if not m:
        raise SystemExit("no `sounds:` table in %s" % path)
    order, bodies = [], {}
    # the table: consecutive .word @sfxN entries
    for w in re.finditer(r"^\s*\.word\s+(@sfx\d+)\s*$", text[m.end():], re.M):
        order.append(w.group(1))
        if len(order) == 15:
            break
    if len(order) != 15:
        raise SystemExit("expected 15 effect pointers, found %d" % len(order))
    for name in order:
        mm = re.search(r"^\s*%s:\s*$" % re.escape(name), text, re.M)
        if not mm:
            raise SystemExit("effect body %s not found" % name)
        body = bytearray()
        for line in text[mm.end():].splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(";"):
                continue
            if line.endswith(":") or line.startswith(".word"):
                break
            if not line.startswith(".byte"):
                break
            for tok in line[5:].split(","):
                tok = tok.strip()
                if not tok:
                    continue
                if tok.startswith("$"):
                    body.append(int(tok[1:], 16))
                elif tok.startswith("'"):
                    body.append(ord(tok[1]))
                else:
                    body.append(int(tok))
        bodies[name] = bytes(body)
    return order, bodies


def parse_noise_tab(path):
    text = open(path, "r", encoding="utf-8", errors="replace").read()
    m = re.search(r"^\s*noise_tab:\s*$", text, re.M)
    if not m:
        raise SystemExit("no noise_tab in %s" % path)
    vals = []
    for line in text[m.end():].splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        if not line.startswith(".byte"):
            break
        for tok in line[5:].split(","):
            tok = tok.strip()
            if tok:
                vals.append(int(tok[1:], 16))
    if len(vals) != 32:
        raise SystemExit("noise_tab should have 32 entries, found %d" % len(vals))
    return vals


def main():
    sounds_path, ftm_path = sys.argv[1], sys.argv[2]
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    order, bodies = parse_sounds(sounds_path)
    noise_tab = parse_noise_tab(ftm_path)
    print("effects: %d  noise_tab: %d entries" % (len(order), len(noise_tab)))

    # Each effect is started on its own stream (the game uses channels 0..2;
    # stream 3 is left idle, which is the case that exposes the sfx_n
    # incumbent-clearing path).
    active = []
    for i, name in enumerate(order):
        body = bodies[name]
        if not body:
            print("  %-6s EMPTY" % name)
            continue
        stream = i % STREAMS
        rec = {"name": name, "stream": stream, "ptr": 0, "off": 0, "rep": 0,
               "buf": bytearray(SF_BUF + 11), "done": False, "log": []}
        rec["ptr"] = 0
        rec["ptr_hi"] = 1          # non-zero: ftm.s treats ptr_hi==0 as inactive
        active.append(rec)
        print("  %-6s stream=%d  %d bytes  head=%s"
              % (name, stream, len(body), body[:12].hex(" ")))

    # sfx_step, exactly as ftm.s:906-952
    def sfx_step(rec, body):
        if rec["done"]:
            return
        if rec["rep"]:
            rec["rep"] -= 1
            return
        while True:
            op = body[rec["off"]]
            rec["off"] += 1
            if op < 0x10:
                val = body[rec["off"]]
                rec["off"] += 1
                rec["buf"][SF_BUF + op] = val
                continue
            if op >= 0xFF:
                rec["done"] = True
                return
            rec["rep"] = op - 0x10
            return

    def ay_out(recs, pairs=None):
        cur_v = [0, 0, 0, 0, 0, 0]
        cur_p = [0, 0, 0, 0, 0, 0]
        ay_n, ay_vn = 0, 0
        # no song loaded: the music contributions are skipped entirely
        for rec in recs:
            b = rec["buf"]
            # The buffer is NES APU register order (famitone.s:970-1016 copies
            # FT_SFX_BUF+n -> FT_OUT_BUF+n): pulse1 volume is the low nibble of
            # buf+0, its period is the 11-bit (buf+2 & 7) << 8 | buf+1.
            v = b[SF_BUF + 0] & 0x0F
            P = ((b[SF_BUF + 2] & 7) << 8) | b[SF_BUF + 1]
            if v and P:
                per = P + ((P * 9 + 32) >> 6)     # N = 1.140293 P, as ftm.s
                if v >= cur_v[0]:
                    cur_v[0], cur_p[0], cur_p[1] = v, per & 0xFF, per >> 8
                    if pairs is not None:
                        pairs.append((P, per))
            # sfx_b: pulse2 -> AY B
            v = b[SF_BUF + 3] & 0x0F
            P = ((b[SF_BUF + 5] & 7) << 8) | b[SF_BUF + 4]
            if v and P:
                per = P + ((P * 9 + 32) >> 6)
                if v >= cur_v[2]:
                    cur_v[2], cur_p[2], cur_p[3] = v, per & 0xFF, per >> 8
                    if pairs is not None:
                        pairs.append((P, per))
            # sfx_c: triangle -> AY C, volume fixed at 15
            if b[SF_BUF + 6]:
                P = ((b[SF_BUF + 8] & 7) << 8) | b[SF_BUF + 7]
                if P:
                    per = P + ((P * 9 + 32) >> 6)
                    if 15 >= cur_v[4]:
                        cur_v[4], cur_p[4], cur_p[5] = 15, per & 0xFF, per >> 8
                        if pairs is not None:
                            pairs.append((P, per))
            # sfx_n: noise.  An idle stream leaves the incumbent alone
            # (ftm.s:854 - clearing it erased noise set by earlier streams).
            v = b[SF_BUF + 9] & 0x0F
            if v:
                if v >= ay_vn:
                    ay_vn = v
                    ay_n = noise_tab[b[SF_BUF + 10] & 0x1F]
        mix = 0x0F
        if cur_v[0]:
            mix &= 0xFE
        if cur_v[2]:
            mix &= 0xFD
        if cur_v[4]:
            mix &= 0xFB
        if ay_vn:
            mix &= 0xF7
        return cur_v, cur_p, ay_n, ay_vn, mix

    # Multi-stream check: all 15 effects live at once across the four streams.
    # This is the case that exposed the sfx_n incumbent-clearing bug - the
    # idle stream 3 ran last and wiped the noise the earlier streams set.
    print("\n--- all effects live across 4 streams (noise-survival check) ---")
    noise_frames = 0
    for f in range(frames):
        for rec in active:
            sfx_step(rec, bodies[rec["name"]])
        cur_v, cur_p, ay_n, ay_vn, mix = ay_out(active)
        if ay_vn:
            noise_frames += 1
        if f < 12:
            perA = cur_p[1] << 8 | cur_p[0]
            perB = cur_p[3] << 8 | cur_p[2]
            perC = cur_p[5] << 8 | cur_p[4]
            print("  f%-3d R7=%02X  A v%-2d N%-5d  B v%-2d N%-5d  C v%-2d N%-5d"
                  "  noise v%-2d N%-2d"
                  % (f, mix, cur_v[0], perA, cur_v[2], perB, cur_v[4], perC,
                     ay_vn, ay_n))
        if not any(not r["done"] for r in active):
            break
    print("  frames with the noise generator audible: %d/%d" % (noise_frames, frames))
    if noise_frames == 0:
        print("  !! noise is silent in every frame - the incumbent is being cleared")

    # Realistic case: game.c starts one effect at a time on channels 0..2
    # (never 3), so each effect is stepped alone with no song loaded.
    print("\n--- per effect, alone on channel 0, no song ---")
    problems = 0
    for i, name in enumerate(order):
        rec = {"name": name, "stream": 0, "off": 0, "rep": 0,
               "buf": bytearray(SF_BUF + 11), "done": False}
        rows = []
        pairs_all = []
        for f in range(frames):
            sfx_step(rec, bodies[name])
            pairs = []
            rows.append(ay_out([rec], pairs) + (f,))
            pairs_all += pairs
            if rec["done"]:
                break
        seen = set()
        dc = []
        silent = True
        for cur_v, cur_p, ay_n, ay_vn, mix, f in rows:
            if cur_v[0]:
                seen.add("toneA")
            if cur_v[2]:
                seen.add("toneB")
            if cur_v[4]:
                seen.add("toneC")
            if ay_vn:
                seen.add("noise")
            if mix != 0x0F:
                silent = False
            if (cur_v[0] and not (cur_p[1] << 8 | cur_p[0])) or \
               (cur_v[2] and not (cur_p[3] << 8 | cur_p[2])) or \
               (cur_v[4] and not (cur_p[5] << 8 | cur_p[4])):
                dc.append(f)
        hz = lambda n: 0 if not n else int(1020432.0 / (16 * n))
        freqs = [hz(n) for P, n in pairs_all if n]
        span = "  %5d..%d Hz" % (min(freqs), max(freqs)) if freqs else ""
        # Pitch fidelity against the NES frequency the same period produces.
        cents = [1200.0 * math.log2((1020432.0 / (16 * n)) / (1789772.5 / (32 * P)))
                 for P, n in pairs_all if n and P]
        tune = "  pitch %+0.1f..%+0.1f cents" % (min(cents), max(cents)) if cents else ""
        print("  %-6s %d frames -> %-22s%s%s"
              % (name, len(rows), ", ".join(sorted(seen)) if seen else "NOTHING",
                 span, tune))
        if cents and (min(cents) < -25.0 or max(cents) > 25.0):
            print("     !! pitch error exceeds 25 cents")
            problems += 1
        if silent:
            print("     !! produced no sound on any frame")
            problems += 1
        if dc:
            print("     !! AY divisor 0 with non-zero volume on frames %s" % dc[:6])
            problems += 1
    if problems:
        print("RESULT: %d problem(s)" % problems)
        return 1
    print("RESULT: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
