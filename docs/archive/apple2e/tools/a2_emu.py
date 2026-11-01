"""6502 + Apple //e core for offline verification of the AE2GAME binary.

Why: every observation channel this host offers is a screenshot of the emulator
window.  It shows pixels and nothing else - no PC, no registers, no memory.  That
is what stalled the port: builds that paint very differently produced byte-identical
frames, and there was no way to tell "the program is not running" from "the program
is running and the paint is wrong".  This runs the real linked binary in software,
so PC, every register, every byte of memory, and the framebuffer are all readable.

The //e state is seeded the way HELLO leaves it, because that is the real input to
BRUN:  COLD at $2000 (BLOAD COLD,A$2000), TILES at $4000, MUSIC at $5000, the four
art screens at $1000/$1200/$1400/$1600, and the BRUN'd image at $6000 with RESET
vector = $6000.  The title-screen path (lv_assets -> hgr_init -> hgr_set_tiles ->
hgr_clear -> hgr_draw_screen -> mb_init -> vram_zero) touches no disk, so RWTS does
not need to be emulated for it.

Usage:
  python tools/a2_emu.py [--trace N] [--max-steps N] [--out PNG] [--stop-at ADDR]
"""
import sys
import argparse

MAIN = bytearray(0x10000)          # main 64K
AUX = bytearray(0x10000)           # aux 64K (//e)

# ---- //e soft-switch state -------------------------------------------------
st = {
    "80store": False,     # $C000 off / $C001 on
    "read_aux": False,    # $C002 main / $C003 aux
    "write_aux": False,   # $C004 main / $C005 aux
    "altzp": False,       # $C008 std / $C009 alt
    "80vid": False,       # $C00C clear / $C00D set
    "text": True,         # $C050 clear(text off -> graphics) / $C051 set
    "mix": False,         # $C052 clear / $C053 set
    "page2": False,       # $C054 page1 / $C055 page2
    "lores": True,        # $C056 lores / $C057 hires
    "dhires": False,      # $C05F off / $C05E on
    "lc_bank": 1,         # $C081/$C083 language card bank
    "rom": True,          # $C081 read ROM / $C082 read RAM
}

LOG = []
WATCH = [False]          # WATCH[0] True -> record writes to $D000-$D0FF with the PC
CURPC = [0]              # PC of the instruction being executed, for the write watch
from collections import Counter as _Counter
PAGEWR = _Counter()      # writes per 256-byte page, to catch a store walking off its area
D000WR = []              # every write to $D000-$D00F, to name whoever clears the COLD image
STACKDELTA = [0]         # bytes pushed minus popped; an ODD value means every later
                         # RTS returns byte-swapped garbage
ODDREPORT = []           # the instruction that first made the depth odd
RTSODD = []              # the first RTS executed at an odd stack depth
# Undocumented 6502 NOPs: opcode -> total instruction size in bytes.
NOP6502 = {0x02: 1, 0x07: 1, 0x0A: 1, 0x14: 2, 0x1A: 1, 0x1C: 3, 0x34: 2,
           0x3A: 1, 0x44: 2, 0x54: 2, 0x74: 2, 0x92: 1, 0xD4: 2, 0xF4: 2}
NOPSEEN = _Counter()     # opcodes we had to skip as a 1-byte NOP
STACKLOG = []            # (pc, op, depth_before, depth_after) inside the mb_init body
PROGWR = []              # every write into the program image $6000-$9BFF, with the pointer cells
ZPWR = []                # writes to cur_ptr ($7E/$7F): (pc, addr, val, cur_ptr after)
KEY = [None]             # injected keypress: rd($C000) returns it with the strobe bit set
KEYSTROBE = [False]      # the strobe is cleared by the first read, like the real register
HOTPC = _Counter()       # executions per PC: the spin loop is the hottest PC
NOMUSIC = [False]        # force FamiTone2's "music playing" flag to 0 every step
KEYEVERY = [0]           # re-arm the injected keypress every N steps
KEYAT = [None]           # PC at which to re-arm the injected keypress
KEYONCE = [0]            # arm the keypress on the Nth visit to KEYAT (1 = the first visit)
KEYVISITS = [0]          # visits so far to KEYAT
WATCHADDR = [None]       # set of addresses whose writes to log
ADDRWR = []              # (pc, addr, val) for the watched addresses
TICKSCALE = [False]      # cut tick_frame's calibrated delay short (frame count stays faithful)
HGRGUARD = [None]        # set of writer PCs whose stores must land in the HGR page
DUMPAT = [None]          # (PC, (base, len)): dump memory through rd() the first time PC executes
OVERRUN = []             # (pc, addr, src_ptr, dst_ptr) for stores outside the HGR page
DSK = [None]             # the packed .dsk bytes, so RWTS can be served from the real image
RWTS_CALLS = [0]         # how many RWTS calls the emulated DOS served


def rd(addr):
    addr &= 0xFFFF
    a = addr >> 8
    if 0xC000 <= addr <= 0xC0FF:
        # Apple II soft switches respond to READS as well as writes.  lv_assets()
        # asserts the language-card bank with "lda $C083", so a read has to fire
        # the switch or the COLD copy is dropped.
        softswitch(addr, 0, True)
        return softswitch_read_status(addr)
    if 0xD000 <= a <= 0xDFFF:
        # Language card: RAM banks 1/2 replace $D000-$DFFF when ROM read is off.
        if not st["rom"]:
            if st["lc_bank"] == 2:
                return MAIN[addr]
            return AUX[addr]
        return MAIN[addr]
    if 0x8000 <= a <= 0xBFFF:
        # I/O space $C000-$C0FF is handled by the caller; $8000-$BFFF is slot ROM.
        return MAIN[addr]
    if st["80store"]:
        # 80STORE on: display stores are split main/aux by page parity.
        if 0x20 <= a <= 0x3F:
            return MAIN[addr] if (a & 1) == 0 else AUX[addr]
        if 0x40 <= a <= 0x7F:
            return MAIN[addr] if (a & 1) == 0 else AUX[addr]
    return MAIN[addr] if not st["read_aux"] else AUX[addr]


def wr(addr, val):
    addr &= 0xFFFF
    val &= 0xFF
    PAGEWR[addr >> 8] += 1
    if HGRGUARD[0] and CURPC[0] in HGRGUARD[0] and not (0x2000 <= addr <= 0x3FFF):
        # hgr_draw_screen's writer aimed outside the HGR page: name the write and
        # the source pointer, which says which stream had run past its terminator.
        if len(OVERRUN) < 40:
            OVERRUN.append((CURPC[0], addr, MAIN[0x80] | (MAIN[0x81] << 8),
                            MAIN[0x7C] | (MAIN[0x7D] << 8),
                            bytes(rd((MAIN[0x80] | (MAIN[0x81] << 8)) + i) for i in range(12))))
    if WATCHADDR[0] and addr in WATCHADDR[0]:
        if len(ADDRWR) < 10000:
            ADDRWR.append((CURPC[0], addr, val))
    if WATCH[0] and addr in (0x7E, 0x7F):
        # cur_ptr is shared by hgr.s and vram.s.  A store loop aimed at $6000 is
        # the program overwriting its own code, so name who loaded $6000 into it.
        if len(ZPWR) < 400:
            ZPWR.append((CURPC[0], addr, val, MAIN[0x7E] | (MAIN[0x7F] << 8)))
    if WATCH[0] and (0x6000 <= addr <= 0x8FFF):
        # A store walking through the program image is self-destruction: the run
        # ends with the program executing $00 (BRK) where its own opcode used to be.
        if len(PROGWR) < 400:
            PROGWR.append((CURPC[0], addr, val,
                           MAIN[0x7C] | (MAIN[0x7D] << 8), MAIN[0x7E] | (MAIN[0x7F] << 8),
                           MAIN[0x80] | (MAIN[0x81] << 8)))
    if WATCH[0] and (0xD000 <= addr <= 0xD00F or 0x2000 <= addr <= 0x200F):
        if 0xD000 <= addr <= 0xD00F and len(D000WR) < 40:
            D000WR.append((CURPC[0], addr, val))
        # Record the hgr.s pointer cells alongside the write so a runaway store
        # names the pointer that ran off.  ZP layout (map-measured):
        #   dst_ptr=$7C  cur_ptr=$7E  src_ptr=$80  tile_base=$82  row_cnt=$84
        #   tag=$85  last=$86  arg_y=$87  fill_v=$88  col_off=$89
        LOG.append((CURPC[0], addr, val,
                    MAIN[0x7C] | (MAIN[0x7D] << 8),
                    MAIN[0x7E] | (MAIN[0x7F] << 8),
                    MAIN[0x80] | (MAIN[0x81] << 8),
                    MAIN[0x84], MAIN[0x87],
                    MAIN[0x94] | (MAIN[0x95] << 8),      # cold_src
                    MAIN[0x96] | (MAIN[0x97] << 8)))     # cold_dst
        if len(LOG) > 60000:
            WATCH[0] = False
    a = addr >> 8
    if 0xC0 <= a <= 0xC0 and 0xC000 <= addr <= 0xC0FF:
        softswitch(addr, val)
        return
    if 0xD000 <= a <= 0xDFFF:
        # Writes to the language-card window always land in LC RAM, whatever the
        # ROM *read* state is: the ROM is not writable, so the bus routes the
        # write to the selected bank.  Gating this on st["rom"] silently dropped
        # lv_assets()'s whole 2,560-byte COLD copy (the copy ran, the watch saw
        # its writes, and $D000 stayed $00), which is why the copy check measured
        # 84/2457 after mb_init had already executed from $D093.
        if st["lc_bank"] == 2:
            MAIN[addr] = val
        else:
            AUX[addr] = val
        return
    if st["80store"]:
        if 0x20 <= a <= 0x3F:
            if (a & 1) == 0:
                MAIN[addr] = val
            else:
                AUX[addr] = val
            return
        if 0x40 <= a <= 0x7F:
            if (a & 1) == 0:
                MAIN[addr] = val
            else:
                AUX[addr] = val
            return
    if st["write_aux"]:
        AUX[addr] = val
    else:
        MAIN[addr] = val


def serve_rwts(cpu):
    """Emulate DOS 3.3's RWTS for a read, serving the sector straight out of the
    packed .dsk.  lvload.s drives DOS only through the page-zero jump at $0100
    with the parameter block at $B8-$C4, so intercepting that one address gives
    the level and art streaming paths real data without a DOS.

    The kit's packer lays the image out as a 16-sector DOS 3.3 master (DOS on
    tracks 0-2, user area from 17), so a (track, sector) pair is at
    track*16*256 + sector*256 - the same mapping tools/a2_tsmap.py reads with.
    Returns the number of bytes copied, or -1 on an out-of-range request."""
    if DSK[0] is None:
        return -1
    slot = MAIN[0xB8]
    drive = MAIN[0xB9]
    buf = MAIN[0xBA] | (MAIN[0xBB] << 8)
    trk = MAIN[0xBD]
    sec = MAIN[0xBE]
    call = MAIN[0xBF]
    off = (trk * 16 + sec) * 256
    RWTS_CALLS[0] += 1
    if call != 2 or off + 256 > len(DSK[0]):
        MAIN[0xC3] = 0x01          # RWTS error: bad request
        MAIN[0xC4] = 0x00
        return -1
    MAIN[buf:buf + 256] = DSK[0][off:off + 256]
    MAIN[0xC1] = sec               # RVSECN: sector actually read
    MAIN[0xC2] = 0
    MAIN[0xC3] = 0                 # RVERR = $0000 -> clean
    MAIN[0xC4] = 0
    return 256


def softswitch_read_status(addr):
    """The byte a soft-switch read returns.  Bit 7 reflects the switch state."""
    a = addr & 0xFF
    if a == 0x00:
        # $C000 read is the //e keyboard data register: bit 7 is the strobe, so a
        # pending keypress reads as the code with bit 7 set.  KEYRESET (a write to
        # $C000) clears it.  Without this the game never sees a key and main()
        # returns straight to DOS.
        if KEY[0] is not None:
            # On a real //e the strobe is part of the register: the FIRST read of
            # $C000 returns the code with bit 7 set, and every later read returns
            # the same code with bit 7 CLEAR until KEYRESET.  input_poll() relies
            # on that - it reads KBD to sample, then reads KBDSTRB to acknowledge.
            # Answering with bit 7 set forever makes pad_trigger() see a key that
            # never goes away.
            val = KEY[0] & 0x7F
            if KEYSTROBE[0]:
                KEYSTROBE[0] = False
                return 0x80 | val
            return val
        return 0x00 if st["80store"] else 0x80
    if a == 0x01:
        return 0x80 if st["80store"] else 0x00
    if a == 0x02:
        return 0x00 if not st["read_aux"] else 0x80
    if a == 0x03:
        return 0x80 if st["read_aux"] else 0x00
    if a == 0x0C:
        return 0x00 if not st["80vid"] else 0x80
    if a == 0x0D:
        return 0x80 if st["80vid"] else 0x00
    if a == 0x11:
        return 0x80          # key available
    if a == 0x18:
        return 0x00          # key strobe
    if a == 0x19:
        return 0x00          # Mockingboard 6522 IRQ line: not asserted
    if a in (0x50, 0x52, 0x54, 0x56, 0x5F):
        return 0x00
    if a in (0x51, 0x53, 0x55, 0x57, 0x5E):
        return 0x00
    if a in (0x81, 0x82):
        return 0x80          # ROM read
    if a in (0x83, 0x8B):
        return 0x00          # RAM read
    return 0x00


def softswitch(addr, val, is_read=False):
    # The low byte of the address is the switch selector: $C000..$C0FF.  Using
    # addr & 0x0F here is wrong - $C083 would decode as $03 and the language-card
    # bank switches ($C081/$C082/$C083/$C08B) would never fire, so writes to
    # $D000-$DFFF are dropped and the COLD image never lands.
    a = addr & 0xFF
    if a == 0x00:
        # $C000 is asymmetric: a READ is the keyboard status (the strobe is part of
        # the register), a WRITE is 80STOREOFF + KEYRESET.  Performing the write
        # action on a read clears the pending key, so the first status read eats
        # the keypress and every later read returns $00 - measured: kbkey came out
        # $00 and the key -> pad-bit table never matched, so PAD_START never
        # appeared and title_screen never left its loop.
        if is_read:
            return
        st["80store"] = False
        KEY[0] = None          # KEYRESET: clears the strobe and the pending key
        KEYSTROBE[0] = False
    elif a == 0x01:
        st["80store"] = True
    elif a == 0x02:
        st["read_aux"] = False
    elif a == 0x03:
        st["read_aux"] = True
    elif a == 0x04:
        st["write_aux"] = False
    elif a == 0x05:
        st["write_aux"] = True
    elif a == 0x08:
        st["altzp"] = False
    elif a == 0x09:
        st["altzp"] = True
    elif a == 0x0C:
        st["80vid"] = False
    elif a == 0x0D:
        st["80vid"] = True
    elif a == 0x50:
        st["text"] = False
    elif a == 0x51:
        st["text"] = True
    elif a == 0x52:
        st["mix"] = False
    elif a == 0x53:
        st["mix"] = True
    elif a == 0x54:
        st["page2"] = False
    elif a == 0x55:
        st["page2"] = True
    elif a == 0x56:
        st["lores"] = True
    elif a == 0x57:
        st["lores"] = False
    elif a == 0x5E:
        st["dhires"] = True
    elif a == 0x5F:
        st["dhires"] = False
    elif a == 0x81:
        st["rom"] = True
        st["lc_bank"] = 1
    elif a == 0x82:
        st["rom"] = False
        st["lc_bank"] = 1
    elif a == 0x83:
        st["rom"] = False
        st["lc_bank"] = 2
    elif a == 0x8B:
        st["rom"] = False
        st["lc_bank"] = 1


class CPU:
    def __init__(self):
        self.a = 0
        self.x = 0
        self.y = 0
        self.sp = 0xFF
        self.p = 0x24          # IRQ disabled, break=1, unused=1
        self.pc = 0
        self.cycles = 0
        self.trace = []

    # ---- flags helpers
    def setzn(self, v):
        self.p = (self.p & ~0x82) | (0x80 if v == 0 else 0) | (v & 0x01 and 0x02)

    def n(self):
        return bool(self.p & 0x80)

    def z(self):
        return bool(self.p & 0x02)

    def v(self):
        return bool(self.p & 0x40)

    def c(self):
        return bool(self.p & 0x01)

    def setc(self, v):
        self.p = (self.p & ~0x01) | (1 if v else 0)

    def push(self, v):
        MAIN[0x0100 + self.sp] = v & 0xFF
        self.sp = (self.sp - 1) & 0xFF

    def pop(self):
        self.sp = (self.sp + 1) & 0xFF
        return MAIN[0x0100 + self.sp]

    def rd16(self, addr):
        lo = rd(addr)
        hi = rd(addr + 1) if (addr + 1) & 0xFF else rd(addr + 1)
        return lo | (hi << 8)

    def wr16(self, addr, v):
        wr(addr, v & 0xFF)
        wr((addr + 1) & 0xFFFF, (v >> 8) & 0xFF)

    def step(self):
        op = rd(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        self.cycles += 1
        return self.exec(op)

    # addressing mode resolvers
    def ea_imm(self):
        v = rd(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return v, 2

    def ea_abs(self):
        lo = rd(self.pc)
        hi = rd(self.pc + 1)
        self.pc = (self.pc + 2) & 0xFFFF
        return lo | (hi << 8), 3

    def ea_zp(self):
        v = rd(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return v, 2

    def ea_zpx(self):
        v = (rd(self.pc) + self.x) & 0xFF
        self.pc = (self.pc + 1) & 0xFFFF
        return v, 2

    def ea_zpy(self):
        v = (rd(self.pc) + self.y) & 0xFF
        self.pc = (self.pc + 1) & 0xFFFF
        return v, 2

    def ea_abx(self):
        a = self.rd16(self.pc)
        self.pc = (self.pc + 2) & 0xFFFF
        return (a + self.x) & 0xFFFF, 2

    def ea_aby(self):
        a = self.rd16(self.pc)
        self.pc = (self.pc + 2) & 0xFFFF
        return (a + self.y) & 0xFFFF, 2

    def ea_izx(self):
        p = (rd(self.pc) + self.x) & 0xFF
        self.pc = (self.pc + 1) & 0xFFFF
        return self.rd16(p), 2

    def ea_izy(self):
        p = rd(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        base = self.rd16(p)
        return (base + self.y) & 0xFFFF, 2

    def ea_absind(self):
        lo = rd(self.pc)
        hi = rd(self.pc + 1)
        self.pc = (self.pc + 2) & 0xFFFF
        # 6502 page-boundary bug on (abs,X) through JMP (addr,X)
        if lo == 0xFF:
            return rd(lo) | (rd((hi << 8)) << 8), 2
        return rd(lo) | (rd(lo + 1) << 8), 2

    def load(self, ea):
        return rd(ea)

    def store(self, ea, v):
        wr(ea, v)

    def rel(self):
        d = rd(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return d - 256 if d >= 128 else d

    def branch(self, cond):
        d = self.rel()
        if cond:
            self.pc = (self.pc + d) & 0xFFFF
            return 1
        return 0

    def exec(self, op):
        A, X, Y = self.a, self.x, self.y
        P = self.p

        def adc(v):
            r = A + v + (1 if self.c() else 0)
            self.setc(r > 0xFF)
            ov = (A ^ v) & 0x80 == 0 and (A ^ r) & 0x80 != 0
            r &= 0xFF
            self.a = r
            self.p = (self.p & ~0x42) | (0x40 if ov else 0) | (0x80 if r & 0x80 else 0) | (0x02 if r == 0 else 0)

        def sbc(v):
            adc((~v) & 0xFF)

        def cmp(v, reg):
            r = (reg - v) & 0xFF
            self.setc(reg >= v)
            self.p = (self.p & ~0x82) | (0x80 if r & 0x80 else 0) | (0x02 if r == 0 else 0)

        def asl(v):
            self.setc(v & 0x80)
            v = (v << 1) & 0xFF
            self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
            return v

        def lsr(v):
            self.setc(v & 1)
            v >>= 1
            self.p = (self.p & ~0x82) | (0x02 if v == 0 else 0)
            return v

        def rol(v):
            c = 1 if self.c() else 0
            self.setc(v & 0x80)
            v = ((v << 1) | c) & 0xFF
            self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
            return v

        def ror(v):
            c = 0x80 if self.c() else 0
            self.setc(v & 1)
            v = (v >> 1) | c
            self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
            return v

        def inc(ea):
            v = (rd(ea) + 1) & 0xFF
            wr(ea, v)
            self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)

        def dec(ea):
            v = (rd(ea) - 1) & 0xFF
            wr(ea, v)
            self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)

        def jsr():
            lo = rd(self.pc)
            hi = rd(self.pc + 1)
            self.pc = (self.pc + 2) & 0xFFFF
            self.push((self.pc - 1) >> 8)
            self.push((self.pc - 1) & 0xFF)
            self.pc = lo | (hi << 8)

        def rts():
            lo = self.pop()
            hi = self.pop()
            self.pc = ((lo | (hi << 8)) + 1) & 0xFFFF

        # ---- the table
        if op == 0x69:
            v, _ = self.ea_imm(); adc(v)
        elif op == 0x65:
            ea, _ = self.ea_zp(); adc(rd(ea))
        elif op == 0x75:
            ea, _ = self.ea_zpx(); adc(rd(ea))
        elif op == 0x6D:
            ea, _ = self.ea_abs(); adc(rd(ea))
        elif op == 0x7D:
            ea, _ = self.ea_abx(); adc(rd(ea))
        elif op == 0x79:
            ea, _ = self.ea_aby(); adc(rd(ea))
        elif op == 0x61:
            ea, _ = self.ea_izx(); adc(rd(ea))
        elif op == 0x71:
            ea, _ = self.ea_izy(); adc(rd(ea))
        elif op == 0x60:
            rts()
        elif op == 0x68:
            # PLA pops the accumulator ONLY.  Popping the flags byte too made PLA
            # consume 2 bytes, so a balanced PHA/PLA pair leaked 1 byte and every
            # later RTS returned byte-swapped - the $25D1 landing into the HGR page.
            self.a = self.pop()
            self.p = (self.p & ~0x30) | (self.a & 0x30)
        elif op == 0x6A:
            self.a = ror(self.a)             # ROR A (was mis-mapped to ASL A)
        elif op == 0x0A:
            self.a = asl(self.a)
        elif op == 0x06:
            ea, _ = self.ea_zp(); wr(ea, asl(rd(ea)))
        elif op == 0x16:
            ea, _ = self.ea_zpx(); wr(ea, asl(rd(ea)))
        elif op == 0x0E:
            ea, _ = self.ea_abs(); wr(ea, asl(rd(ea)))
        elif op == 0x1E:
            ea, _ = self.ea_abx(); wr(ea, asl(rd(ea)))
        elif op == 0xCA:
            self.x = (self.x - 1) & 0xFF
            self.p = (self.p & ~0x82) | (0x80 if self.x & 0x80 else 0) | (0x02 if self.x == 0 else 0)
        elif op == 0xBA:
            self.x = self.sp
            self.p = (self.p & ~0x82) | (0x80 if self.x & 0x80 else 0) | (0x02 if self.x == 0 else 0)
        elif op == 0xB8:
            self.p &= ~0x40
        elif op == 0x1A:
            self.x = (self.x - 1) & 0xFF
            self.p = (self.p & ~0x82) | (0x80 if self.x & 0x80 else 0) | (0x02 if self.x == 0 else 0)
        elif op == 0x8A:
            self.a = self.x
            self.p = (self.p & ~0x82) | (0x80 if self.x & 0x80 else 0) | (0x02 if self.x == 0 else 0)
        elif op == 0x9A:
            self.sp = self.x
        elif op == 0xAA:
            self.x = self.a
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0xA8:
            self.y = self.a
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x98:
            self.a = self.y
            self.p = (self.p & ~0x82) | (0x80 if self.y & 0x80 else 0) | (0x02 if self.y == 0 else 0)
        elif op == 0x88:
            self.y = (self.y - 1) & 0xFF
            self.p = (self.p & ~0x82) | (0x80 if self.y & 0x80 else 0) | (0x02 if self.y == 0 else 0)
        elif op == 0xE8:
            self.x = (self.x + 1) & 0xFF
            self.p = (self.p & ~0x82) | (0x80 if self.x & 0x80 else 0) | (0x02 if self.x == 0 else 0)
        elif op == 0xC8:
            self.y = (self.y + 1) & 0xFF
            self.p = (self.p & ~0x82) | (0x80 if self.y & 0x80 else 0) | (0x02 if self.y == 0 else 0)
        elif op == 0x4A:
            self.a = lsr(self.a)
        elif op == 0x46:
            ea, _ = self.ea_zp(); wr(ea, lsr(rd(ea)))
        elif op == 0x56:
            ea, _ = self.ea_zpx(); wr(ea, lsr(rd(ea)))
        elif op == 0x4E:
            ea, _ = self.ea_abs(); wr(ea, lsr(rd(ea)))
        elif op == 0x5E:
            ea, _ = self.ea_abx(); wr(ea, lsr(rd(ea)))
        elif op == 0x2A:
            self.a = rol(self.a)
        elif op == 0x26:
            ea, _ = self.ea_zp(); wr(ea, rol(rd(ea)))
        elif op == 0x36:
            ea, _ = self.ea_zpx(); wr(ea, rol(rd(ea)))
        elif op == 0x2E:
            ea, _ = self.ea_abs(); wr(ea, rol(rd(ea)))
        elif op == 0x3E:
            ea, _ = self.ea_abx(); wr(ea, rol(rd(ea)))
        elif op == 0x6A:
            self.a = ror(self.a)
        elif op == 0x66:
            ea, _ = self.ea_zp(); wr(ea, ror(rd(ea)))
        elif op == 0x76:
            ea, _ = self.ea_zpx(); wr(ea, ror(rd(ea)))
        elif op == 0x6E:
            ea, _ = self.ea_abs(); wr(ea, ror(rd(ea)))
        elif op == 0x7E:
            ea, _ = self.ea_abx(); wr(ea, ror(rd(ea)))
        elif op == 0xA9:
            v, _ = self.ea_imm(); self.a = v
            self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xA5:
            ea, _ = self.ea_zp(); self.a = rd(ea)
            v = self.a; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xB5:
            ea, _ = self.ea_zpx(); self.a = rd(ea)
            v = self.a; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xAD:
            ea, _ = self.ea_abs(); self.a = rd(ea)
            v = self.a; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xBD:
            ea, _ = self.ea_abx(); self.a = rd(ea)
            v = self.a; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xB9:
            ea, _ = self.ea_aby(); self.a = rd(ea)
            v = self.a; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xA1:
            ea, _ = self.ea_izx(); self.a = rd(ea)
            v = self.a; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xB1:
            ea, _ = self.ea_izy(); self.a = rd(ea)
            v = self.a; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xA2:
            v, _ = self.ea_imm(); self.x = v
            self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xA6:
            ea, _ = self.ea_zp(); self.x = rd(ea)
            v = self.x; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xB6:
            ea, _ = self.ea_zpy(); self.x = rd(ea)
            v = self.x; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xAE:
            ea, _ = self.ea_abs(); self.x = rd(ea)
            v = self.x; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xBE:
            ea, _ = self.ea_aby(); self.x = rd(ea)
            v = self.x; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xA0:
            v, _ = self.ea_imm(); self.y = v
            self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xA4:
            ea, _ = self.ea_zp(); self.y = rd(ea)
            v = self.y; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xB4:
            ea, _ = self.ea_zpx(); self.y = rd(ea)
            v = self.y; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xAC:
            ea, _ = self.ea_abs(); self.y = rd(ea)
            v = self.y; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0xBC:
            ea, _ = self.ea_abx(); self.y = rd(ea)
            v = self.y; self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0x85:
            ea, _ = self.ea_zp(); wr(ea, self.a)
        elif op == 0x95:
            ea, _ = self.ea_zpx(); wr(ea, self.a)
        elif op == 0x8D:
            ea, _ = self.ea_abs(); wr(ea, self.a)
        elif op == 0x9D:
            ea, _ = self.ea_abx(); wr(ea, self.a)
        elif op == 0x99:
            ea, _ = self.ea_aby(); wr(ea, self.a)
        elif op == 0x81:
            ea, _ = self.ea_izx(); wr(ea, self.a)
        elif op == 0x91:
            ea, _ = self.ea_izy(); wr(ea, self.a)
        elif op == 0x86:
            ea, _ = self.ea_zp(); wr(ea, self.x)
        elif op == 0xA6 and False:
            pass
        elif op == 0x8E:
            ea, _ = self.ea_abs(); wr(ea, self.x)
        elif op == 0x96:
            ea, _ = self.ea_zpy(); wr(ea, self.x)
        elif op == 0x84:
            ea, _ = self.ea_zp(); wr(ea, self.y)
        elif op == 0x94:
            ea, _ = self.ea_zpx(); wr(ea, self.y)
        elif op == 0x8C:
            ea, _ = self.ea_abs(); wr(ea, self.y)
        elif op == 0x82:
            ea, _ = self.ea_aby(); wr(ea, self.y)   # STY abs,Y
        elif op == 0x80:
            ea, _ = self.ea_izx(); wr(ea, self.y)   # STY ($00,X)
        elif op == 0x9C:
            ea, _ = self.ea_abs(); wr(ea, 0)        # STZ abs (65c02)
        elif op == 0x29:
            v, _ = self.ea_imm(); self.a &= v
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x25:
            ea, _ = self.ea_zp(); self.a &= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x35:
            ea, _ = self.ea_zpx(); self.a &= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x2D:
            ea, _ = self.ea_abs(); self.a &= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x3D:
            ea, _ = self.ea_abx(); self.a &= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x39:
            ea, _ = self.ea_aby(); self.a &= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x21:
            ea, _ = self.ea_izx(); self.a &= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x31:
            ea, _ = self.ea_izy(); self.a &= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x24:
            ea, _ = self.ea_zp(); v = rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0x2C:
            ea, _ = self.ea_abs(); v = rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if v & 0x80 else 0) | (0x02 if v == 0 else 0)
        elif op == 0x09:
            v, _ = self.ea_imm(); self.a |= v
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x05:
            ea, _ = self.ea_zp(); self.a |= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x15:
            ea, _ = self.ea_zpx(); self.a |= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x0D:
            ea, _ = self.ea_abs(); self.a |= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x1D:
            ea, _ = self.ea_abx(); self.a |= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x19:
            ea, _ = self.ea_aby(); self.a |= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x01:
            ea, _ = self.ea_izx(); self.a |= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x11:
            ea, _ = self.ea_izy(); self.a |= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x49:
            v, _ = self.ea_imm(); self.a ^= v
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x45:
            ea, _ = self.ea_zp(); self.a ^= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x55:
            ea, _ = self.ea_zpx(); self.a ^= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x4D:
            ea, _ = self.ea_abs(); self.a ^= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x5D:
            ea, _ = self.ea_abx(); self.a ^= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x59:
            ea, _ = self.ea_aby(); self.a ^= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x41:
            ea, _ = self.ea_izx(); self.a ^= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0x51:
            ea, _ = self.ea_izy(); self.a ^= rd(ea)
            self.p = (self.p & ~0x82) | (0x80 if self.a & 0x80 else 0) | (0x02 if self.a == 0 else 0)
        elif op == 0xE9:
            v, _ = self.ea_imm(); sbc(v)
        elif op == 0xE5:
            ea, _ = self.ea_zp(); sbc(rd(ea))
        elif op == 0xF5:
            ea, _ = self.ea_zpx(); sbc(rd(ea))
        elif op == 0xED:
            ea, _ = self.ea_abs(); sbc(rd(ea))
        elif op == 0xFD:
            ea, _ = self.ea_abx(); sbc(rd(ea))
        elif op == 0xF9:
            ea, _ = self.ea_aby(); sbc(rd(ea))
        elif op == 0xE1:
            ea, _ = self.ea_izx(); sbc(rd(ea))
        elif op == 0xF1:
            ea, _ = self.ea_izy(); sbc(rd(ea))
        elif op == 0xC9:
            v, _ = self.ea_imm(); cmp(v, self.a)
        elif op == 0xC5:
            ea, _ = self.ea_zp(); cmp(rd(ea), self.a)
        elif op == 0xD5:
            ea, _ = self.ea_zpx(); cmp(rd(ea), self.a)
        elif op == 0xCD:
            ea, _ = self.ea_abs(); cmp(rd(ea), self.a)
        elif op == 0xDD:
            ea, _ = self.ea_abx(); cmp(rd(ea), self.a)
        elif op == 0xD9:
            ea, _ = self.ea_aby(); cmp(rd(ea), self.a)
        elif op == 0xC1:
            ea, _ = self.ea_izx(); cmp(rd(ea), self.a)
        elif op == 0xD1:
            ea, _ = self.ea_izy(); cmp(rd(ea), self.a)
        elif op == 0xE0:
            v, _ = self.ea_imm(); cmp(v, self.x)
        elif op == 0xE4:
            ea, _ = self.ea_zp(); cmp(rd(ea), self.x)
        elif op == 0xEC:
            ea, _ = self.ea_abs(); cmp(rd(ea), self.x)
        elif op == 0xC0:
            v, _ = self.ea_imm(); cmp(v, self.y)
        elif op == 0xC4:
            ea, _ = self.ea_zp(); cmp(rd(ea), self.y)
        elif op == 0xCC:
            ea, _ = self.ea_abs(); cmp(rd(ea), self.y)
        elif op == 0xE6:
            ea, _ = self.ea_zp(); inc(ea)
        elif op == 0xF6:
            ea, _ = self.ea_zpx(); inc(ea)
        elif op == 0xEE:
            ea, _ = self.ea_abs(); inc(ea)
        elif op == 0xFE:
            ea, _ = self.ea_abx(); inc(ea)
        elif op == 0xC6:
            ea, _ = self.ea_zp(); dec(ea)
        elif op == 0xD6:
            ea, _ = self.ea_zpx(); dec(ea)
        elif op == 0xCE:
            ea, _ = self.ea_abs(); dec(ea)
        elif op == 0xDE:
            ea, _ = self.ea_abx(); dec(ea)
        elif op == 0x4C:
            ea, _ = self.ea_abs(); self.pc = ea
        elif op == 0x6C:
            ea, _ = self.ea_absind(); self.pc = self.rd16(ea)
        elif op == 0x20:
            jsr()
        elif op == 0x40:
            # RTI: pop P, then pop the return address.  This used to be
            # "pc = rd16(0xFFFA)" - jump to the NMI vector and pop NOTHING - so
            # every BRK (which pushes 3 bytes) leaked 3 bytes and restarted the
            # program at $6000.  That is the whole 3-byte stack leak, and it is
            # why an RTS at $D131 returned the byte-swapped $25D1.
            self.p = self.pop()
            lo = self.pop()
            hi = self.pop()
            self.pc = lo | (hi << 8)
        elif op == 0x42:
            # $42 is a one-byte NOP on a 6502, not a vector jump.
            pass
        elif op == 0x00:
            # BRK: push PC+2, push P|0x30, IRST=1, PC = IRQ vector
            self.pc = (self.pc + 1) & 0xFFFF
            self.push(self.pc >> 8)
            self.push(self.pc & 0xFF)
            self.push(self.p | 0x30)
            self.p |= 0x04
            self.pc = self.rd16(0xFFFE)
        elif op == 0x48:
            self.push(self.a)
        elif op == 0x08:
            self.push(self.p | 0x30)
        elif op == 0x28:
            self.p = (self.pop() & ~0x30) | (self.p & 0x30)
        elif op == 0x10:
            self.branch(not self.n())        # BPL
        elif op == 0x30:
            self.branch(self.n())            # BMI
        elif op == 0x50:
            self.branch(not self.v())        # BVC
        elif op == 0x70:
            self.branch(self.v())            # BVS
        elif op == 0x90:
            self.branch(not self.c())        # BCC
        elif op == 0xB0:
            self.branch(self.c())            # BCS
        elif op == 0xD0:
            self.branch(not self.z())        # BNE
        elif op == 0xF0:
            self.branch(self.z())            # BEQ
        elif op == 0x18:
            self.setc(False)                 # CLC: clear the carry
        elif op == 0x38:
            self.setc(True)                  # SEC: set the carry
        elif op == 0xD8:
            self.p &= ~0x08                  # CLD: clear the decimal flag (bit 3)
        elif op == 0xB8:
            self.p &= ~0x40                  # CLV: clear the overflow flag (bit 6)
        elif op == 0x58:
            self.p &= ~0x04                  # CLI
        elif op == 0x78:
            self.p |= 0x04                   # SEI
        elif op == 0xEA:
            pass
        elif op in NOP6502:
            # The 6502's undocumented NOPs, by instruction size.  These matter
            # because a stray jump into the HGR page executes art bytes, and the
            # trace has to keep going to name the jump that did it.
            self.pc = (self.pc + NOP6502[op] - 1) & 0xFFFF
        else:
            NOPSEEN[op] += 1
            self.pc = (self.pc + 1) & 0xFFFF
        return op


def seed():
    """Load the disk payloads into memory exactly as HELLO leaves them."""
    import os
    files = [
        (r'build\a2\game.bin', 0x6000),
        (r'build\a2\cold.bin', 0x2000),      # BLOAD COLD,A$2000
        (r'build\hgr_tiles.bin', 0x4000),
        (r'build\a2\music.bin', 0x5000),
        # HELLO preloads the two startup screens at fixed non-overlapping
        # addresses; GAMEOVERH/WELLDONEH are streamed on demand via RWTS, which
        # this core does not emulate.
        (r'build\art\titleh.bin', 0x1000),
        (r'build\art\creditsh.bin', 0x1900),
    ]
    for path, addr in files:
        if not os.path.exists(path):
            print("MISSING %s" % path)
            continue
        data = open(path, "rb").read()
        for i, b in enumerate(data):
            MAIN[addr + i] = b
        print("  loaded %-28s -> $%04X  %d bytes" % (os.path.basename(path), addr, len(data)))
    # RESET vector -> the BRUN entry point
    MAIN[0xFFFA] = 0x00
    MAIN[0xFFFB] = 0x60
    MAIN[0xFFFE] = 0x00
    MAIN[0xFFFF] = 0xF0      # a BRK-return trap: NMI/IRQ land in a known spot
    MAIN[0xFFFC] = 0x00
    MAIN[0xFFFD] = 0xF0
    # A stray BRK jumps through the IRQ vector.  With $F000 left as zeros that is
    # BRK -> $0000 -> BRK, which pushes 3 bytes each time and byte-shifts every
    # later RTS - the artifact that made an RTS look like it returned into the HGR
    # page.  An RTI at the vector makes a BRK behave like it does on a real //e
    # under the Monitor: return to the instruction after the BRK.
    MAIN[0xF000] = 0x40              # RTI
    for p in ('build\\a2\\ae2_game.dsk',):
        if os.path.exists(p):
            DSK[0] = open(p, "rb").read()
            print("  loaded disk image for RWTS: %s (%d bytes)" % (p, len(DSK[0])))
            break


def render_hgr(path):
    """Render $2000-$3FFF as HGR 280x192 using the verified scanline layout.

    The colour rule is the real NTSC artifact, copied from the kit's own
    emulator (pom2games/dev/tools/a2run/a2run.c:374-418), which is the
    reference for what AppleWin shows:
        pal[hi][x&1]:  hi=0 -> violet (even col) / green (odd col);
                       hi=1 -> blue   (even col) / orange (odd col).
        a pixel with a lit neighbour (x-1 or x+1) reads WHITE (the colour
        period spans two dots); an isolated dot takes its column colour and
        is drawn two pixels wide.
    """
    from PIL import Image
    PAL = ((0xD0, 0x43, 0xE5), (0x2F, 0xB8, 0x1F),   # [hi=0] violet, green
           (0x1A, 0x8F, 0xFF), (0xF0, 0x6A, 0x1C))   # [hi=1] blue,   orange
    WHITE = (0xFF, 0xFF, 0xFF)
    im = Image.new("RGB", (280, 192))
    px = im.load()
    for y in range(192):
        addr = 0x2000 + (y % 8) * 0x0400 + ((y // 8) % 8) * 0x80 + (y // 64) * 0x28
        # on[x] / hi[x]: pixel x (0..279) lit? and its byte's bit7.
        on = [0] * 282                       # 1-indexed: on[1+x] = pixel x
        hi = [0] * 280
        for byte in range(40):
            b = MAIN[addr + byte]
            for k in range(7):
                on[1 + byte * 7 + k] = (b >> k) & 1
                hi[byte * 7 + k] = b >> 7
        col = [0] * 280
        for x in range(280):
            if on[1 + x]:
                col[x] = WHITE if (on[x] or on[2 + x]) else PAL[hi[x] * 2 + (x & 1)]
        # a colour dot is two pixels wide on screen (one colour period)
        for x in range(279, 0, -1):
            if not on[1 + x] and on[x] and col[x - 1] != WHITE:
                col[x] = col[x - 1]
        for x in range(280):
            px[x, y] = col[x]
    im.save(path)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--max-steps', type=int, default=2_000_000)
    ap.add_argument('--trace', type=int, default=0)
    ap.add_argument('--dump-mem', default=None,
                    help='dump memory at exit through the same rd() routing the CPU sees: ADDR:LEN hex, e.g. 0x1000:0x810')
    ap.add_argument('--dump-at', default=None, nargs=2, metavar=('PC', 'MEM'),
                    help='dump MEM (ADDR:LEN) through rd() the first time PC is executed, to a file')
    ap.add_argument('--dump-hgr', default=None,
                    help='dump the HGR page to a text file at exit: 40 bytes per scanline, in display order')
    ap.add_argument('--out', default='build/a2/emu_hgr.png')
    ap.add_argument('--stop-at', type=lambda x: int(x, 0), default=None)
    ap.add_argument('--report-every', type=int, default=200_000)
    ap.add_argument('--watch', action='store_true',
                    help='record writes to $D000-$D0FF and $2000-$200F with the PC and pointer cells')
    ap.add_argument('--probe', default=None,
                    help='comma-separated addresses: print the hgr.s pointer cells each time the PC hits one')
    ap.add_argument('--key', default=None,
                    help='ASCII code to inject, e.g. 0x0D for RETURN.  rd($C000) answers with the code and '
                         'the strobe bit set until KEYRESET is written, which is how the //e keyboard works.')
    ap.add_argument('--key-once', default=0, type=int,
                    help='with --key-at, arm ONE keypress on the Nth visit to that PC (1 = the first visit). '
                         'pad_trigger() reports only newly-pressed bits, so arming on every poll makes it return 0, '
                         'and arming on the first visit hands the press to whichever screen polls first.')
    ap.add_argument('--key-at', default=None,
                    help='PC at which to re-arm the injected keypress (e.g. 0x8B0D = the input_poll stub), so the '
                         'routine that maps keys to pad bits is the one that consumes the strobe')
    ap.add_argument('--key-every', default=0, type=int,
                    help='re-arm the injected keypress every N steps (a screen that waits for START consumes the strobe)')
    ap.add_argument('--fast-tick', action='store_true',
                    help='cut tick_frame\'s calibrated 208x256 delay short so many frames are cheap to simulate '
                         '(the frame COUNT stays faithful; only the per-frame cycle cost is reduced)')
    ap.add_argument('--hgr-guard', default=None,
                    help='comma-separated writer PCs: report every store they make outside $2000-$3FFF, '
                         'with the source pointer at that moment')
    ap.add_argument('--watch-addr', default=None,
                    help='comma-separated addresses: log every write to them with the PC that made it')
    ap.add_argument('--nomusic', action='store_true',
                    help='force the FamiTone2 "music playing" flag to 0 every step (isolate the music path)')
    a = ap.parse_args()

    print("seeding //e memory from the disk payloads:")
    seed()

    cpu = CPU()
    cpu.pc = 0x6000
    cpu.sp = 0xFF
    out_text = []
    stopped = None
    steps = 0
    trace = []
    history = []          # ring of executed (pc, op) for the tail of a bad run
    last_in = None
    escaped = None
    page_hit = None
    probe_addrs = set()
    probe_hits = 0
    NOMUSIC[0] = bool(a.nomusic)
    KEYEVERY[0] = int(a.key_every)
    if a.key_at is not None:
        KEYAT[0] = int(a.key_at, 0)
    KEYONCE[0] = int(a.key_once)
    if a.watch_addr:
        WATCHADDR[0] = {int(x, 0) for x in a.watch_addr.split(',')}
    TICKSCALE[0] = bool(a.fast_tick)
    if a.hgr_guard:
        HGRGUARD[0] = {int(x, 0) for x in a.hgr_guard.split(',')}
    if a.dump_at:
        base, ln = a.dump_at[1].split(':')
        DUMPAT[0] = (int(a.dump_at[0], 0), (int(base, 0), int(ln, 0)))
    if a.key is not None:
        KEY[0] = int(a.key, 0)
        KEYSTROBE[0] = True
        print("  injecting keypress: $%02X (%r)" % (KEY[0], chr(KEY[0])))
    if a.probe:
        probe_addrs = {int(x, 0) for x in a.probe.split(',')}
    WATCH[0] = bool(a.watch)
    while steps < a.max_steps:
        if a.stop_at is not None and cpu.pc == a.stop_at:
            stopped = "stop-at $%04X" % a.stop_at
            break
        pc_before = cpu.pc
        CURPC[0] = pc_before
        # DOS's RWTS is reached through the page-zero jump at $0100.  Serving it
        # from the packed image is what lets the level and art streaming paths run
        # here at all; the return address is the one the caller's JSR pushed.
        if DUMPAT[0] is not None and pc_before == DUMPAT[0][0]:
            base, ln = DUMPAT[0][1]
            out = "build/a2/at_%04X_%04X.bin" % (base, ln)
            with open(out, 'wb') as f:
                f.write(bytes(rd(base + i) for i in range(ln)))
            print("DUMP-AT pc=$%04X dumped $%04X:$%04X to %s" % (pc_before, base, ln, out))
            DUMPAT[0] = None
        if pc_before == 0x0100:
            serve_rwts(cpu)
            lo = cpu.pop()
            hi = cpu.pop()
            cpu.pc = ((lo | (hi << 8)) + 1) & 0xFFFF
            continue
        if probe_addrs and pc_before in probe_addrs and probe_hits < 12:
            probe_hits += 1
            print("  probe $%04X hit %2d: depth=%d SP=$%02X dst=$%04X cur=$%04X src=$%04X row_cnt=$%02X arg_y=$%02X tag=$%02X last=$%02X A=$%02X X=$%02X cold_src=$%04X cold_dst=$%04X lc_bank=%d rom=%s"
                  % (pc_before, probe_hits, (0xFF - cpu.sp) & 0xFF, cpu.sp,
                     MAIN[0x7C] | (MAIN[0x7D] << 8), MAIN[0x7E] | (MAIN[0x7F] << 8),
                     MAIN[0x80] | (MAIN[0x81] << 8), MAIN[0x84], MAIN[0x87],
                     MAIN[0x85], MAIN[0x86], cpu.a, cpu.x,
                     MAIN[0x94] | (MAIN[0x95] << 8), MAIN[0x96] | (MAIN[0x97] << 8),
                     st["lc_bank"], st["rom"]))
        op = cpu.step()
        if pc_before == 0x61B4 and MAIN[0x80] | (MAIN[0x81] << 8) == 0x1809:
            sp = MAIN[0x80] | (MAIN[0x81] << 8)
            print("  TERM-PROBE src=$%04X bytes: %s  rawMAIN_180A=$%02X rawAUX_180A=$%02X rd180A=$%02X"
                  % (sp, ' '.join('%02X' % rd(sp + k) for k in range(12)),
                     MAIN[0x180A], AUX[0x180A], rd(0x180A)))
        if pc_before in (0x61B8, 0x61BA):
            print("  TRACE PC=$%04X op=$%02X  src_lo=$%02X src_hi=$%02X P=$%02X Z=%d next_pc=$%04X raux=%d waux=%d"
                  % (pc_before, op, MAIN[0x80], MAIN[0x81], cpu.p, cpu.p & 0x02, cpu.pc,
                     st["read_aux"], st["write_aux"]))
        if pc_before in (0x61A3, 0x61A5):
            print("  REP-PROBE PC=$%04X op=$%02X  A=$%02X P=$%02X Z=%d next_pc=$%04X src=$%04X"
                  % (pc_before, op, cpu.a, cpu.p, cpu.p & 0x02, cpu.pc,
                     MAIN[0x80] | (MAIN[0x81] << 8)))
        if KEY[0] is not None and KEYAT[0] is not None and pc_before == KEYAT[0]:
            # The //e strobe is part of the key register: the first read of $C000
            # takes it, so a periodic re-arm gets consumed by whichever routine
            # happens to read the keyboard first.  Arming at input_poll's entry
            # guarantees the routine that maps keys to pad bits is the one that
            # sees the strobe.  The test must use the PC BEFORE the step: the stub
            # is a JMP, so after the step the PC is already inside input_poll.
            #
            # Arming on EVERY visit is itself a trap: pad_trigger() reports only
            # bits that were NOT already down, so a key held on every poll is
            # latched and pad_trigger() returns 0 forever.  --key-once arms a
            # single press, which is what a real player does.
            if KEYONCE[0]:
                KEYVISITS[0] += 1
                if KEYVISITS[0] >= KEYONCE[0]:
                    KEYSTROBE[0] = True
                    KEYONCE[0] = 0        # one press, at the Nth visit
            else:
                KEYSTROBE[0] = True
        if TICKSCALE[0] and cpu.pc == 0xD005:
            # tick_frame's calibrated delay is 208 x 256 inner iterations, which is
            # correct on real hardware (~268k cycles = 59.9 Hz) but costs ~107k
            # instructions per frame here.  Cutting the inner loop short keeps the
            # frame COUNT faithful while making many frames cheap to simulate.
            cpu.a = (cpu.a - 1) & 0xFF
            cpu.pc = 0xD007
        if KEY[0] is not None and KEYEVERY[0] and (steps % KEYEVERY[0]) == 0:
            # A title screen that waits for START consumes the strobe and then
            # waits forever.  Re-arm the keypress so the game advances.
            KEYSTROBE[0] = True
        if NOMUSIC[0]:
            # FamiTone2's per-frame music path is taken only when $DA27 != 0 and
            # $DA28 != 0.  Forcing $DA27 to 0 makes ftm_tick take the no-music
            # path, which isolates whether the spin loop is music processing.
            MAIN[0xDA27] = 0
        HOTPC[pc_before] += 1
        # Log every stack-depth change inside the mb_init body so the single
        # instruction that pops (or pushes) one byte too many is named outright.
        if 0xD093 <= pc_before <= 0xD131:
            d2 = (0xFF - cpu.sp) & 0xFF
            if d2 != STACKDELTA[0] and len(STACKLOG) < 200:
                STACKLOG.append((pc_before, op, STACKDELTA[0], d2))
            STACKDELTA[0] = d2
        # A JSR/RTS pair is 2 bytes, so a well-formed call chain keeps the stack
        # depth EVEN.  An odd depth (a stray PHA, or a 3-byte BRK push) makes every
        # later RTS return a byte-swapped address - the signature of the $25D1
        # landing.  Name the instruction that first tips it odd.
        depth = (0xFF - cpu.sp) & 0xFF
        if depth & 1 and not ODDREPORT:
            ODDREPORT.append((pc_before, op, depth, cpu.sp,
                              bytes(MAIN[0x0100 + cpu.sp:0x0100 + cpu.sp + 8])))
        # A PHA/PLA pair makes the depth transiently odd, so that alone is not the
        # leak.  The leak is an RTS that runs while the depth is odd: its return
        # address is then byte-swapped.  Name it, with the call chain behind it.
        if op == 0x60 and depth & 1 and not RTSODD:
            RTSODD.append((pc_before, depth, cpu.sp, list(history)))
        history.append((pc_before, op))
        if len(history) > 400:
            history.pop(0)
        steps += 1
        # Report the first time control leaves the program image.  This is the
        # single most useful fact when a run goes bad: the ROM area is not
        # emulated, so a jump into it means the program called a vector that
        # this core does not implement.
        if escaped is None:
            # The first time the PC executes a byte of the HGR page is the real
            # fault: the page is all $00, so that is BRK, and BRK pushes PC+2 and
            # jumps through the IRQ vector.  That is where a bogus return address
            # like $3ED1 gets onto the stack.
            if 0x2000 <= cpu.pc <= 0x3FFF and not (0x2000 <= pc_before <= 0x3FFF):
                page_hit = (pc_before, op, cpu.pc, cpu.sp, list(history))
            inside = lambda p: (0x6000 <= p <= 0x9FFF) or (0xD000 <= p <= 0xDFFF)
            if inside(pc_before) and not inside(cpu.pc):
                escaped = (pc_before, op, cpu.pc)
                # An RTS that lands outside the program is a stack problem, and
                # the stack bytes below the return address name the chain that
                # went wrong.
                escaped = escaped + (cpu.sp, cpu.a, cpu.x, cpu.y,
                                      bytes(MAIN[0x0100 + cpu.sp:0x0100 + cpu.sp + 16]),
                                      list(history))
        if a.trace and steps <= a.trace:
            trace.append("step %7d PC=$%04X op=$%02X A=$%02X X=$%02X Y=$%02X SP=$%02X P=$%02X"
                         % (steps, (cpu.pc - 1) & 0xFFFF, op, cpu.a, cpu.x, cpu.y, cpu.sp, cpu.p))
        # DOS warm start reached -> the program exited
        if cpu.pc == 0x03D0:
            stopped = "reached DOSWARM $03D0 (program exited)"
            break
        if cpu.pc == 0xFFF0:
            stopped = "hit the NMI/IRQ trap at $FFF0"
            break
        if a.report_every and steps % a.report_every == 0:
            print("  step %d  PC=$%04X  A=$%02X X=$%02X Y=$%02X SP=$%02X"
                  % (steps, cpu.pc, cpu.a, cpu.x, cpu.y, cpu.sp))
    print("steps: %d  %s" % (steps, stopped or "ran out of steps"))
    if page_hit:
        print("FIRST EXECUTION OF THE HGR PAGE: PC=$%04X executed op=$%02X and landed at $%04X (SP=$%02X)"
              % (page_hit[0], page_hit[1], page_hit[2], page_hit[3]))
        print("   last %d instructions before it:" % len(page_hit[4]))
        print("   " + ' '.join('%04X:%02X' % (p, o) for p, o in page_hit[4][-70:]))
    if escaped:
        print("FIRST ESCAPE from the program: PC=$%04X executed op=$%02X and landed at $%04X"
              % (escaped[0], escaped[1], escaped[2]))
        print("   at that moment SP=$%02X A=$%02X X=$%02X Y=$%02X"
              % (escaped[3], escaped[4], escaped[5], escaped[6]))
        print("   stack at $0100+SP: %s" % escaped[7].hex(' '))
        # The tail of the executed instruction stream, oldest first.  For a bad
        # RTS this is the call chain that produced the bogus return address.
        tail = escaped[8]
        print("   last %d executed instructions (oldest first):" % len(tail))
        print("   " + ' '.join('%04X:%02X' % (p, o) for p, o in tail))
    else:
        print("never left the program image")
    # Who wrote the language-card bank's head?  Group by the PC that made the
    # write so a corrupted COLD image names its writer.
    if LOG:
        from collections import Counter
        cnt = Counter(e[0] for e in LOG)
        print("watched writes: %d, by PC:" % len(LOG))
        for pc, n in cnt.most_common(10):
            print("   PC=$%04X  %d writes" % (pc, n))
        # Show the first few writes made by the non-lv_assets PCs, with the
        # pointer cells as they stood at that instruction.
        shown = 0
        for e in LOG:
            if e[0] == 0x88E5:
                continue
            print("   PC=$%04X addr=$%04X val=$%02X | dst=$%04X cur=$%04X src=$%04X row=$%02X argy=$%02X cold_src=$%04X cold_dst=$%04X"
                  % (e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8], e[9]))
            shown += 1
            if shown >= 8:
                break
    for line in trace:
        print(line)

    # Report the state of the paint
    nz = sum(1 for i in range(0x2000, 0x4000) if MAIN[i])
    print("HGR page $2000-$3FFF nonzero bytes: %d of 8192" % nz)
    print("writes by 256-byte page (top 12):")
    for pg, n in PAGEWR.most_common(12):
        print("   $%02X00-$%02XFF  %d writes" % (pg, pg, n))
    print("soft switches: 80store=%s 80vid=%s lores=%s text=%s page2=%s write_aux=%s lc_bank=%d rom=%s"
          % (st["80store"], st["80vid"], st["lores"], st["text"], st["page2"],
             st["write_aux"], st["lc_bank"], st["rom"]))
    print("COLD at $D000: %s" % ("present" if rd(0xD000) else "absent"))
    print("RWTS calls served from the disk image: %d" % RWTS_CALLS[0])
    hot = [(pc, n) for pc, n in HOTPC.most_common(12) if n > 50]
    if hot:
        print("hottest PCs (executions) - the spin loop is at the top:")
        for pc, n in hot:
            print("   PC=$%04X  %d executions" % (pc, n))
    if a.dump_mem:
        base, ln = a.dump_mem.split(':')
        base, ln = int(base, 0), int(ln, 0)
        # A colon is not legal in a Windows filename, so build the name from the parts.
        out = "build/a2/mem_%04X_%04X.bin" % (base, ln)
        with open(out, 'wb') as f:
            f.write(bytes(rd(base + i) for i in range(ln)))
        print("dumped $%04X:$%04X through rd() to %s" % (base, ln, out))
    if a.dump_hgr:
        # 40 bytes per scanline in DISPLAY order, using the same verified layout
        # render_hgr() uses, so a stripe pattern can be read off the bytes directly.
        with open(a.dump_hgr, 'w') as f:
            for y in range(192):
                addr = 0x2000 + (y % 8) * 0x0400 + ((y // 8) % 8) * 0x80 + (y // 64) * 0x28
                f.write('y=%3d  %s\n' % (y, ' '.join('%02X' % MAIN[addr + b] for b in range(40))))
        print("dumped the HGR page to %s" % a.dump_hgr)
    if OVERRUN:
        print("stores outside the HGR page $2000-$3FFF (the RLE writer ran past its terminator):")
        for pc, a_, src, dst, peek in OVERRUN:
            print("   PC=$%04X  wrote $%04X   src_ptr=$%04X  dst_ptr=$%04X  at src: %s"
                  % (pc, a_, src, dst, ' '.join('%02X' % b for b in peek)))
    if ADDRWR:
        print("writes to the watched addresses (PC -> value):")
        for pc, a_, v in ADDRWR[:80]:
            print("   PC=$%04X  $%04X <= $%02X" % (pc, a_, v))
        if len(ADDRWR) > 80:
            print("   ... %d more" % (len(ADDRWR) - 80))
        with open('build/a2/addrwr_all.txt', 'w') as f:
            for pc, a_, v in ADDRWR:
                f.write("PC=$%04X  $%04X <= $%02X\n" % (pc, a_, v))
    if ZPWR:
        print("writes to cur_ptr ($7E/$7F):")
        for i, (pc, a_, v, cur) in enumerate(ZPWR[30:70]):
            print("   [#%d] PC=$%04X  $%02X = $%02X   cur_ptr=$%04X" % (30 + i, pc, a_, v, cur))
        hits = [w for w in ZPWR if w[1] == 0x7F and w[2] >= 0x40]
        print("   writes setting cur_ptr high byte >= $40: %d" % len(hits))
        for pc, a_, v, cur in hits[:12]:
            print("   PC=$%04X  $7F = $%02X   cur_ptr=$%04X" % (pc, v, cur))
    if NOPSEEN:
        print("opcodes skipped as 1-byte NOPs (unimplemented - these corrupt the trace):")
        for op, n in NOPSEEN.most_common(20):
            print("   $%02X  x%d" % (op, n))
    if PROGWR:
        bypc = _Counter(pc for pc, a_, v, d, c, s in PROGWR)
        print("writes into the program image $6000-$9BFF: %d recorded, by PC:" % len(PROGWR))
        for pc, n in bypc.most_common(8):
            print("   PC=$%04X  %d writes" % (pc, n))
        for pc, a_, v, d, c, s in PROGWR[:14]:
            print("   PC=$%04X -> $%04X = $%02X | dst=$%04X cur=$%04X src=$%04X" % (pc, a_, v, d, c, s))
    if STACKLOG:
        print("stack-depth changes inside $D093-$D131 (%d):" % len(STACKLOG))
        for pc, op, d0, d1 in STACKLOG[:40]:
            print("   PC=$%04X op=$%02X  depth %d -> %d" % (pc, op, d0, d1))
    if RTSODD:
        pc, depth, sp, hist = RTSODD[0]
        print("FIRST RTS AT ODD STACK DEPTH: PC=$%04X depth=%d (SP=$%02X)" % (pc, depth, sp))
        print("   call chain behind it (oldest first):")
        print("   " + ' '.join('%04X:%02X' % (p, o) for p, o in hist[-60:]))
    if ODDREPORT:
        pc, op, depth, sp, s = ODDREPORT[0]
        print("FIRST ODD STACK DEPTH: after PC=$%04X op=$%02X depth=%d (SP=$%02X)" % (pc, op, depth, sp))
        print("   stack at $0100+SP: %s" % s.hex(' '))
    if D000WR:
        print("every write to $D000-$D00F (%d recorded):" % len(D000WR))
        for pc, a_, v in D000WR:
            print("   PC=$%04X -> $%04X = $%02X" % (pc, a_, v))
    # Compare the COLD image in RAM with the file, byte for byte.  lv_assets()
    # copies it from the $2000 staging page into the language-card bank; if the
    # copy is short or offset, a jump into a stub reads zeros.
    import os
    if os.path.exists(r'build\a2\cold.bin'):
        want = open(r'build\a2\cold.bin', "rb").read()
        # Read through rd(), the same routing the CPU uses.  Reading MAIN directly
        # disagreed with the write log, which showed PC=$8911 storing byte-exact
        # COLD bytes at $D000-$D00F.
        got = bytes(rd(0xD000 + i) for i in range(len(want)))
        bad = [i for i in range(len(want)) if got[i] != want[i]]
        print("COLD copy check: %d/%d bytes match, %d differ"
              % (len(want) - len(bad), len(want), len(bad)))
        if bad:
            i = bad[0]
            print("  first mismatch at $D000+$%04X = $D000+$%04X: ram=$%02X file=$%02X"
                  % (i, i, got[i], want[i]))
            print("  ram  around: %s" % got[max(0, i - 8):i + 8].hex(" "))
            print("  file around: %s" % want[max(0, i - 8):i + 8].hex(" "))
    render_hgr(a.out)
    print("wrote %s" % a.out)


if __name__ == "__main__":
    main()
