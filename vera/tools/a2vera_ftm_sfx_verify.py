#!/usr/bin/env python3
"""Execute the linked FTM SFX routines as 6502 code and inspect each frame."""
from pathlib import Path
import re
import sys

from py65.devices.mpu6502 import MPU

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "vera/build"


class VeraMemory(list):
    def __init__(self):
        super().__init__([0] * 65536)
        self.cursor = 0
        self.psg = {}

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if key == 0xC202:
            self.cursor = self[0xC200] | (self[0xC201] << 8) | ((value & 0x0F) << 16)
        elif key == 0xC203:
            self.psg[self.cursor] = value
            if (self[0xC202] >> 4) == 1:
                self.cursor = (self.cursor + 1) & 0x1FFFF


def symbol(map_text, name):
    match = re.search(r"^" + re.escape(name) + r"\s+([0-9A-F]{6})\s+RLA", map_text, re.M)
    if not match:
        raise ValueError(f"missing {name} in linker map")
    return int(match.group(1), 16)


def bss_address(map_text):
    start = re.search(r"^BSS\s+([0-9A-F]{6})\s+", map_text, re.M)
    module = re.search(r"^ftm_sfx_simple2\.o:\s*\n\s+BSS\s+Offs=([0-9A-F]{6})", map_text, re.M)
    if not start or not module:
        raise ValueError("missing SFX BSS layout")
    return int(start.group(1), 16) + int(module.group(1), 16)


def call(mpu, addr):
    # RTS pops $9FFF and advances to $A000.
    mpu.memory[0x1FF] = 0x9F
    mpu.memory[0x1FE] = 0xFF
    mpu.sp = 0xFD
    mpu.pc = addr
    trail = []
    for _ in range(50000):
        if mpu.pc == 0xA000:
            return
        trail.append(f"{mpu.pc:04X}:{mpu.memory[mpu.pc]:02X}")
        if len(trail) > 16:
            trail.pop(0)
        if mpu.pc == 0 and len(trail) > 1:
            raise RuntimeError("SFX routine reached PC=$0000: " + " ".join(trail))
        mpu.step()
    raise RuntimeError(f"SFX routine did not return; PC=${mpu.pc:04X}: {' '.join(trail)}")


def verify(index, count, verbose):
    linker = (BUILD / "level2.map").read_text(encoding="ascii")
    memory = VeraMemory()
    for address, name in ((0x1000, "AEMUSIC2#061000"), (0x2000, "AE2VERA2#062000")):
        image = (BUILD / "stage" / name).read_bytes()
        memory[address:address + len(image)] = image
    mpu = MPU(memory=memory, pc=0)
    base = bss_address(linker)
    mpu.a = index
    call(mpu, symbol(linker, "_ftm_sfx_start"))
    if verbose:
        print(f"SFX {index:02d}: start=${symbol(linker, '_ftm_sfx_start'):04X}, BSS=${base:04X}")
    audible = 0
    ultrasonic = 0
    ended = False
    for frame in range(count):
        call(mpu, symbol(linker, "_ftm_sfx_tick"))
        data = memory[base:base + 23]
        ptr = data[0] | (data[1] << 8)
        period = data[3] | ((data[4] & 7) << 8)
        phase = data[16] | (data[17] << 8)
        voices = []
        for voice in range(4):
            addr = 0x1F9D0 + voice * 4
            freq = memory.psg.get(addr, 0) | (memory.psg.get(addr + 1, 0) << 8)
            gain = memory.psg.get(addr + 2, 0) & 63
            if freq and gain:
                voices.append(f"{voice + 4}:${freq:04X}/v{gain}")
                if freq >= 0xE000:
                    ultrasonic += 1
        audible += bool(voices)
        if verbose:
            print(f"{frame:02d}: ptr=${ptr:04X} repeat={data[13]:3} "
                  f"pulse_ctl=${data[2]:02X} timer=${period:03X} "
                  f"voices={','.join(voices) or '-'}")
        if not ptr >> 8:
            ended = True
            break
    return audible, frame + 1, ended, ultrasonic


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "all":
        for index in range(15):
            audible, frames, ended, ultrasonic = verify(index, 180, False)
            print(f"SFX {index:02d}: {audible} audible / {frames} frames, "
                  f"ended={ended}, ultrasonic={ultrasonic}")
            if not audible or not ended:
                raise SystemExit(f"SFX {index:02d} failed")
    else:
        index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 15
        verify(index, count, True)


if __name__ == "__main__":
    main()
