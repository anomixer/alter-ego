# Porting an a2vera game to the Commander X16 — working guide

This is the reusable checklist distilled from the Alter Ego port (Apple II + VERA → Commander
X16, 2026-11-05/06).  The reference implementation every section points at lives in
[`x16/`](../): `x16/spike/asset_cx16.c`, `input_cx16.s`, `gate_cx16.s`, `loader.s`,
`game.cfg`, `build.ps1`, and the write-up in
[`x16/docs/PORT-CX16-EVAL.md`](PORT-CX16-EVAL.md) (English; Traditional Chinese in
`PORT-CX16-EVAL-tw.md`).

> The Traditional Chinese version of this guide is
> [`A2VERA-to-CX16-tw.md`](A2VERA-to-CX16-tw.md) — same content, translated 2026-11-06.

It assumes the source project looks like a typical **a2vera** game: cc65 C (`main.c`) plus ca65
assembly (`title.s`, `oam.s`, `music_*.s`, `ftm_*.s`, `input.s`), VERA at slot `$C200/$C400`,
ProDOS `open/read/close`, Applesoft/Monitor ROM, an `input.s` that reads `$C000`/`$C010` and the
game port PB0/PB1/PDL, and a `STARTUP.BAS` that BLOADs the music and BRUNs the game.  The next
planned target is `freegemas` a2vera, so the guide leans on "how Alter Ego's pieces were
rewritten" rather than on Alter Ego specifics.

**Bottom line up front:** the VERA layer transfers almost for free (same registers, different
base address), and the real work is five things — **file I/O, the boot chain, input, the frame
cadence, and the zero-page/memory budget**.  Budget three to four weeks for a first port, most of
it on the first two.

---

## 0. What actually changes, in one table

| Layer | Apple II + VERA | Commander X16 | Effort |
| --- | --- | --- | --- |
| VERA registers | base `$C200`/`$C400` | base `$9F20` | **copy the macros** |
| Screen/tiles/sprites/PSG logic | — | identical | none |
| CPU | 6502/65C02 @ 1 MHz | 65C02S @ 8 MHz | none (but see timing) |
| Main RAM | 48–64 KB linear | `$0000-$9EFF` fixed, `$A000-$BFFF` banked | check the linker map |
| I/O | `$C000-$CFFF` slots | `$9F00-$9FFF` | rewrite the reads |
| File system | ProDOS MLI | KERNAL `LOAD` over HostFS/DOS | **rewrite** |
| Boot | `STARTUP.BAS` (BLOAD/BRUN) | `$0801` PRG loader, `-prg -run` | **rewrite** |
| Keyboard | `$C000` latch, `$C010` strobe | KERNAL `GETIN` + `joystick_get` | **rewrite** |
| Interrupts | VERA VSYNC polled | KERNAL IRQ is driven by VERA VSYNC | **rework** |
| Music timing | ~40 loops/s, 1.5× compensation | VSYNC-locked 60/s, no compensation | **delete the compensation** |

---

## 1. Before changing a line: inventory

### 1.1 Measure the Apple II build

Build it once with a map file and write down:

- the `CODE`/`BSS` extents and the highest address (it has to fit under `$9EFF`);
- zero-page usage (`$00-$FF`), especially anything at `$9A-$9F` (`ftm_envelopes.s` used those,
  and `$9D-$A8` is reserved on the X16 — see §4);
- the asset list and sizes (`TILES`, palettes, title/credits, level files, music);
- the exact Apple II-only code paths (grep is your friend): `$C0`, `PEKA`/`poke`, `open(`,
  `read(`, `close(`, `STARTUP`, `KBDSTRB`, `keyboard_model`, `iobuf`.

### 1.2 Grep for platform dependencies

```text
$C000  $C010  $C020  $C030  PDL  pdl  KBD  KBDSTRB  ROM  Monitor
open  read  close  SETNAM?  ProDOS  MLI
text  gotoxy  print  BASIC
```

Every hit is either rewritten or wrapped in `#ifndef VERA_X16` (dead on the X16, and it buys you
memory — §4).

### 1.3 List the VERA features used

Layer 0 (tiles or bitmap), sprites/OAM, palette, PSG channels, H/V scroll, scaling
(`DC_HSCALE/VSCALE`), IRQ use.  All of it transfers; only the base address moves.  If the game
uses bitmap mode, check the tile base addresses against the X16's defaults — the X16 also boots
with layer 0 configured, so you must overwrite `L0_CFG/MAP/TIL` yourself (do not "inherit").

### 1.4 Decide the machine assumptions

512 KB banked RAM is always there; the X16 boots without DOS in the drive.  Do **not** assume
cmdr-dos is present unless you ship an SD image — HostFS (the emulator's `-fsroot`) and DOS are
two different worlds (§5).

---

## 2. Toolchain and build flags

Use the same cc65 (2.19) and switch the target:

```powershell
ca65 --cpu 65C02 ...                 # was --cpu 6502 (the X16 is a 65C02S)
cl65 -t cx16 -Oirs -DVERA_BASE=0x9F20 ...
```

- `-t cx16` gives you `cx16.lib` + `cx16.cfg` (`STARTADDRESS $0801`, ZP `$22-$7F`,
  `__HIMEM__ $9F00`, `__STACKSIZE__ $0800`).  Override the RAM area in your own `game.cfg`, e.g.
  `RAM: load = $2000, type = rw;` and see §4.
- Keep the Apple II build working from the **same sources**: gate every change with
  `#ifdef VERA_X16` and keep `-t apple2` building.  At the end, compile both spellings and
  compare the listings (`6,166 instructions, 0 differing lines` was the Alter Ego acceptance
  test — see §9).
- VERA macros: define your own base once.

```c
#ifdef VERA_X16
#define VERA_BASE 0x9F20
#else
#define VERA_BASE 0xC200
#endif
```

If the a2vera project uses ca65 macros, pass `-D VERA_BASE=$9F20` instead.  Note that
**`VERA_BASE` is an assembler constant** in the `.s` files while `main.c` uses
`-DVERA_BASE=0x9F20`; keep both spellings in sync.

---

## 3. The VERA layer

The same chip, the same offsets — only `$C200`/`$C400` becomes `$9F20`:

| Purpose | Apple II | X16 |
| --- | --- | --- |
| Address low/mid/high | base+$00/$01/$02 | `$9F20/$9F21/$9F22` |
| Data 0/1 | base+$03/$04 | `$9F23/$9F24` |
| Control | base+$05 | `$9F25` |
| IRQ enable/status | base+$06/$07 | `$9F26/$9F27` |
| Display mode | base+$29 | `$9F29` |
| Layer0 cfg/map/til | base+$2C/$2D/$2E | `$9F2C/$9F2D/$9F2E` |
| Scroll | base+$2F/$30 | `$9F2F/$9F30` |
| OAM / PSG / palette | `$1FC00` / `$1F9C0` / `$1FA00` | identical |

Three pitfalls that cost the most time in the Alter Ego port:

1. **The 16-bit `VERA.address` field truncates the 17th address bit.**  `cx16.h` exposes
   `VERA.address` (16 bits) and `address_hi` (A16 in bit 0, increment in bits 6-4).  Writing
   `VERA.address = 0x10000` silently becomes 0.  Use:

   ```c
   VERA.address = addr & 0xFFFF;
   VERA.address_hi = 0x10 | ((addr >> 16) & 1);   /* + increment bits 6-4 */
   ```

2. **`struct __vera` has no `video` field**, so `VERA.video` does not compile; use
   `*(volatile unsigned char *)0x9F29`.

3. **`DC_VIDEO` `0x01` is only the output mode** (VGA); you need `0x51` for VGA + layer 0 +
   sprites.  The Apple II build's `0x51` is still right, but if you compute the value, do not
   forget the layer bit.

Everything else — palette writes, tilemaps, OAM, PSG — can be copied from the Apple II build
verbatim.

---

## 4. Memory map, zero page, and the last 6 bytes

X16 memory:

```
$0000-$9EFF   fixed RAM (your program must fit here)
$9F00-$9FFF   I/O (VERA at $9F20-$9F3F, SMC, etc.) — NEVER touch
$A000-$BFFF   512 KB banked RAM (bank selected at $00; cc65 uses its own bank)
$C000-$FFFF   ROM (BASIC/KERNAL)
```

Zero page on the X16: `$02-$21` r0-r15, `$22-$7F` free for cc65, `$80-$9C` KERNAL/DOS, `$9D-$A8`
**reserved**, `$A9-$D3` maths library, `$D4-$FF` BASIC.

- If the port has constants at `$9A-$9F` (FamiTone envelopes in Alter Ego), move them into
  `$22-$7F` and reserve them in the linker config.  Alter Ego still runs with them at `$9A-$9F`,
  but that is a latent bug — do it before hardware.
- Give the BSS a little breathing room.  Alter Ego's `game.cfg` ends up with **6 bytes** free;
  that is normal, and it is why the next section exists.

### 4.1 Freeing memory without changing the Apple II build

Two techniques, both used in `x16/`:

1. **Wrap Apple II dead code.**  `KEYBOARD`/`KBDSTRB`/`keyboard_model` blocks,
   `keyboard_level_reset`, the pause menu's latch test — put `#ifndef VERA_X16` around them.
   That recovered ~96 B of CODE and 3 B of BSS in Alter Ego.
2. **A hole segment.**  When the C version of a function no longer fits, write it in assembly and
   drop it into a linker-map hole (Alter Ego's `gate_cx16.s` sits at `$92DC`, between `FTMTABLE`
   and `FTM_HIGH_BSS`):

   ```text
   GATE: load = RAM, type = ro, start = $92DC;
   ```

   Find holes by reading the map file (`ld65 -m game.map`) and looking for gaps between your
   segments — then verify the region is really free in the loader image (the loader loads the
   whole image, padding included, so a `fill = yes` image is fine).

Check every build with the map: `ld65: Segment 'BSS' overflows memory area 'BSS' by N bytes`
means "cut dead code or find a hole", not "raise the area".

---

## 5. File I/O: KERNAL LOAD over HostFS

Rewrite the asset layer (Alter Ego: `x16/spike/asset_cx16.c` + `kload_cx16.s`).  The sequence is:

```c
/* one file, headerless, to a chosen address/bank */
ae_load(name, sa, addr, bank);       /* SETNAM/SETLFS, then jsr $FFD5 */
```

Implementation notes that matter:

1. **File names must be lower case.**  x16emu r49's HostFS compares the raw `SETNAM` bytes, so
   `"GAME"` returns `A=4` (FILE NOT FOUND) and `"game"` loads.  Lower-case every name at the
   point where you send it (`ae_lname()` in `asset_cx16.c`); the Apple II side can keep its
   upper-case names.
2. **The carry flag from `LOAD` is untrustworthy** — it is set (`P=31`) even on success.  Check
   `A` (0 = OK, 4 = not found, …), never `bcs fail`.
3. **`SA=2` is the VRAM-friendly form** (no header, address in `X/Y`, bank in `A`): use it to load
   a palette or tilemap straight into `$1xxxx`.  `SA=1` expects a 2-byte header; `SA=3` is
   bank1.  Alter Ego's assets go `SA=2` with `A=3` for `$1FA00`-class destinations.
4. **A target address of `$0000` is not accepted.**  Stage at `$A000` and copy, which is exactly
   what `ae_load_raw_asset()` does.
5. **Mask IRQs and switch `RAM_BANK=1`** around the load if you are staging in banked RAM, then
   restore; end with `CLRCHN` (`$FFCC`) or `GETIN` will keep reading from the file instead of the
   keyboard.
6. **Do not let your `read()` clobber the VERA address.**  In the level streamer, `read()` is
   called while `load_level_file()` is writing to `VERA_DATA0`; saving and restoring
   `VERA.address`/`address_hi` around every byte read is what fixed the black screen in Alter
   Ego (`x16/spike/io_cx16.c`).
7. **HostFS vs DOS:** `-fsroot` is for development; for a real release put the files on an SD
   image and use DOS.  `-sdcard` is the closest thing to hardware.

Skeletons (sketches of the reference implementation, not compile-ready):

```c
/* asset_cx16.c — the reference also controls $B9 (RAM bank) and does the LOAD
 * from asm, so the staging area and the bank are under its control. */
static char ae_name[16];

extern unsigned char ae_kload(unsigned char sa, unsigned int addr);  /* jsr $FFD5 */

static void ae_lname(void) {                    /* HostFS compares SETNAM bytes */
    for (char *p = ae_name; *p; ++p)
        if (*p >= 'A' && *p <= 'Z') *p = (char)(*p + ('a' - 'A'));
}

unsigned char ae_load(const char *name, unsigned char sa,
                      unsigned int addr, unsigned char bank)
{
    unsigned char i = 0, st;
    while (name[i] && i < 15) { ae_name[i] = name[i]; ++i; }
    ae_name[i] = 0;
    ae_lname();
    __asm__("sei");
    *(volatile unsigned char *)0x00 = bank;     /* RAM_BANK */
    cbm_k_setlfs(2, 8, sa);                     /* channel 2, device 8, SA */
    cbm_k_setnam(ae_name);
    st = ae_kload(sa, addr);
    ae_clrchn();                                /* GETIN back to the keyboard */
    __asm__("cli");
    return st;                                  /* 0 = OK, 4 = FILE NOT FOUND */
}
```

```asm
; kload_cx16.s — the only magic is "jsr $FFD5"
; in: A = secondary address, X/Y = load address, $B9 = RAM bank
_ae_kload:
        jsr     $FFD5
        rts                 ; A = status (0 = OK); carry is unreliable
```

For the exact register conventions see `x16/spike/kload_cx16.s` and the loader in
`x16/spike/loader.s` (`music_name: .byte "music"`, `game_name: .byte "game"`).

---

## 6. The boot chain

The Apple II's `STARTUP.BAS` (BLOAD music → BRUN game) becomes a **`$0801` PRG with a BASIC
`SYS` stub**:

```basic
10 SYS 2061
```

The stub is only there so `-prg loader.prg -run` and `LOAD "loader.prg",8,1` + `RUN` both work.
The loader then:

1. `LOAD "music",8,1` to the overlay address (`$1000` in Alter Ego), then
2. `LOAD "game",8,1` to `$2000` (2-byte header form is fine here), then
3. `jmp $2000`.

Keep a `$9FB9` beacon letter per stage while bringing this up — it is the cheapest progress lamp
the emulator gives you (§10).

For release, either keep a directory + `AUTOBOOT.X16`, or build an SD image with the same files
under their **upper-case** names (DOS does not need the HostFS lower-case rule — but test it).

---

## 7. Input

Replace `input.s`.  On the X16:

- **`joystick_get` (`$FF56`) device 0 is the KERNAL keyboard joystick** and reflects the live held
  state — use it for the directions and for A/B.  `Y=0` on return means "present"; the SNES pad
  devices are 1-4 (`Y=$FF` = not connected).
- **Make directions and A/B level-sensitive**; make **START/SELECT rising-edge single-frame
  pulses** (otherwise `Enter` reopens the pause menu every frame).  De-duplicate repeated
  actions in game logic (Alter Ego's `exchange_input_lock`), not in the input layer.
- **Delete the old "hold timer" compensation.**  Reading `$C000`/`$C010` on the X16 returns ROM
  bytes: `$C000` reads as a constant, which turns into "a direction is held forever".
  If you keep key events as a fallback (`Space`, `1`, special keys), that is fine, but do not
  let the fallback run when the keyboard joystick is present.
- **Cheat sequences:** do not compare `pad == code[i]` every frame — a held button stays equal on
  the next frame and resets the index.  Count **changes** instead:

  ```c
  static unsigned char code_last_pad;
  ...
  if (pad != code_last_pad) {          /* one step per press */
      code_last_pad = pad;
      if (pad == code[code_index]) { ... }
  }
  ```
- Add `CLRCHN` after every KERNAL `LOAD` before calling `GETIN` (§5 item 5).

Key events still cost you the ~0.5 s auto-repeat delay, which is why the Alter Ego X16 build
dropped `WASD` and uses the keyboard joystick for movement.

---

## 8. Frame cadence and music — the one that surprises people

**The X16 KERNAL's 60 Hz IRQ is sourced from the VERA VSYNC interrupt.**  If you clear
`VERA_IEN` to poll `VERA_ISR` (a very natural thing to copy from the Apple II build), the KERNAL
IRQ stops entirely: the jiffy clock freezes, keyboard scanning stops, `GETIN` always returns 0,
and it looks like "the buttons do nothing".

Correct pattern:

1. Chain the KERNAL IRQ, do not replace it:

   ```asm
   _ae_irq_install:
           lda     $0314
           sta     _old_irq
           lda     $0315
           sta     _old_irq+1
           lda     #<_ae_irq
           sta     $0314
           lda     #>_ae_irq
           sta     $0315
           rts
   _ae_irq:
           inc     _ae_irq_frames          ; 16-bit frame counter
           bne     forward
           inc     _ae_irq_frames+1
   forward:
           jmp     (_old_irq)
   ```

2. `vera_sync_init()` on the X16 only does `VERA_ISR = 0x0F; VERA_IEN = 0x01;` and installs the
   hook; leave the KERNAL's clearing of `ISR` alone.
3. `wait_frame()` waits for `_ae_irq_frames` to change (or use the KERNAL's jiffy).

Then fix the **timing compensation**: a slow Apple II loop usually runs the game logic "1.5 NES
steps per iteration" and the music "1.5 source ticks per iteration".  On a 60 Hz VSYNC-locked X16
loop that becomes **1.5× too fast** (the hero walks ≈90 px/s instead of 60).  Gate both with
`#ifdef VERA_X16` and use one step / one tick per frame.  Sanity check: measure walking speed in
px/s against the NES original.

If the result then feels slightly slow, add a **tempo trim** with an 8-bit accumulator
(1/256 tick per frame) instead of changing the tick rate — no long-term drift:

```c
temp_tempo += AE_X16_TEMPO_TRIM;      /* 8 ≈ +3.1% */
if (temp_tempo >= 256) { temp_tempo -= 256; extra_tick = 1; }
```

---

## 9. Behaviour fixes that X16 ports typically need

Alter Ego had three game-feel bugs that the Apple II build never showed; the pattern generalises:

1. **"Only 1 in N frames accepts the button."**  The NES original checks the exchange only when
   the player is not moving; during a fall that is one frame per 8 px row.  On the Apple II, the
   `$C010` any-key flag (level-sensitive) happened to cover it; on the X16 with a pulse it is a
   1-in-8 chance.  Fix: do the check every frame **inside `#ifdef VERA_X16`**.
2. **"Falls through the floor after a mid-air action."**  An animation that freezes between tile
   rows leaves a non-zero step counter, and the next gravity step skips the floor test.  Fix:
   snap the position back to the row and clear the step counter when the animation ends.
3. **"Teleport moves land inside a wall."**  Vertically mirrored levels (`y = 240 - y`) can
   mirror into solid tiles.  Fix: only allow the teleport when the destination has floor,
   otherwise keep falling and switch at the first legal frame.

Keep each fix inside `#ifdef VERA_X16`, then prove the Apple II build did not move:

```powershell
cl65 -t apple2 --cpu 6502 -Oirs ...   # old and new, dump the listings
# same instruction count, 0 differing lines, only .export lines added
```

Write a **geometry simulation** over the level data (`x16/spike/fallswap_sim.py` did this for
Alter Ego: 65,667 situations, 756 floor-throughs before, 0 after).  It runs in a second, without
the emulator, and it is the only way to be sure a "sometimes it falls through" bug is really gone.

---

## 10. Testing and automation

- **Beacons:** writing to `$9FB9` makes x16emu print `User debug 1: $xx` on stdout — a free
  progress log for the loader and the asset layer.  Pack payloads into one byte when you need
  frame alignment (three bytes per frame occasionally get dropped).
- **VRAM dump:** `-dump V` + `$9FB5=1` + jump to `$FFFF` → `dump.bin` (128 KB VRAM + composer +
  palette + layer registers), comparable byte-for-byte against the assets.
- **Screenshots:** a foreground `PrintWindow`/`BitBlt` capture works; the emulator does not have
  to cooperate (`x16/tools/shot.ps1`).
- **Synthetic keys need real scan codes:** `keybd_event(vk, MapVirtualKey(vk, 0), flags)`.
  `SendKeys`/`SendMessage` carry no scan code and never reach the guest; arrows also need
  `KEYEVENTF_EXTENDEDKEY` (down `1`, up `|2`).  Steal the foreground, verify you actually got it
  (`GetForegroundWindow() == hwnd`), and fail loudly otherwise — otherwise you photograph
  somebody else's window.
- **Always kill the emulator in `try/finally`:** a leftover process with redirected stdout makes
  the caller look hung forever.
- **Audio:** `-Wav <file.wav>` records; force-killing leaves the RIFF lengths unwritten, so patch
  them before analysing (RMS/peak per segment) — `x16/spike/wavstat.py`.

Acceptance checklist (Alter Ego's, reuse as-is):

| Check | How |
| --- | --- |
| Boots to the title | `-prg LOADER.PRG -run`, screenshot |
| All assets land | VRAM dump vs host file; beacon per asset |
| Level 1 renders and is playable | Enter → arrows → action → pause menu |
| Special keys / cheats | `T`/`M`/`N`/`1`, cheat sequence, screenshots |
| Music and SFX | `-Wav` + RMS/peak per segment |
| Cadence | walking px/s vs the NES original |
| Both builds compile | `-t cx16` and `-t apple2`, Apple II listing diff = 0 |
| Headless smoke test | keys + screenshots, no human clicking |

---

## 11. Browser build on GitHub Pages (optional but cheap)

Alter Ego's `web/x16/` runs the real `dist/` on the official X16Community WebAssembly release:

1. Pin the release (`x16emu_wasm-r49.zip`) and its **SHA-256**; download + verify at site-build
   time, cache it in a gitignored directory, and never commit the archive.
2. Copy your asset files **lower-cased** into `site/x16/game/`, plus a `manifest.json` listing
   them (§5's case rule applies here too — the browser file system is case-sensitive).
3. `Module` config: `arguments: ['-prg', 'loader.prg', '-run', '-ram', '512', ...]`,
   `locateFile: n => 'emulator/' + n`, and a `preRun` that fetches every file and
   `FS.writeFile('/' + name, bytes)` before removing the run dependency.
4. Audio needs a user gesture: call the wasm hook (`j2c_start_audio`) and only report "sound on"
   once `Module.SDL2.audioContext.state === 'running'`.
5. Ship the emulator/ROM licence texts next to the page; the ROM is not open source, only
   licensed for X16 use.

The whole thing is ~200 lines of JS plus a 60-line build script; see `web/x16/`.

---

## 12. Packaging

| Form | When | Notes |
| --- | --- | --- |
| Directory + `-fsroot` | development | lower-case names (HostFS) |
| `AUTOBOOT.X16` directory | share/hand-off | still HostFS/DOS-dependent |
| `.zip` / SD image | release | upper-case names are fine on DOS; test on real hardware |

Keep artifact names stable and versioned (`<game>-x16-…`), and never rename an existing release.

---

## 13. Troubleshooting table

| Symptom | Cause | Fix |
| --- | --- | --- |
| “None of the buttons work” | `VERA_IEN` zeroed → KERNAL IRQ dead → `GETIN` always 0 | chain `$0314/$0315`, never zero `IEN` (§8) |
| Title screen full of stripes/noise | assets never loaded | lower-case `SETNAM` names (§5) |
| Black screen when entering a level | `read()` reset `VERA.address` mid-write | save/restore the VERA pointer around `read()` |
| `LOAD` returns `A=4` | file name case | lower-case the name |
| `LOAD` “fails” but data is fine | carry is always 1 | test `A`, not carry |
| Assets missing at `$0000` | KERNAL LOAD rejects address 0 | stage at `$A000`, copy |
| `GETIN` returns garbage after a load | input channel still points at the file | `CLRCHN` (`$FFCC`) after each load |
| Tap walks one tile too far | old hold-timer compensation | remove it; use the keyboard joystick |
| Tap action ignored 7 times out of 8 | check only runs on landing frames | check every frame in `#ifdef VERA_X16` |
| Hero falls through the floor after a mid-air move | animation freezes between rows, step counter left over | snap to the row, clear the counter |
| Teleport lands inside a wall | mirrored destination has no floor | validate the destination, defer until legal |
| Everything ~1.5× too fast | Apple II’s “1.5 steps/tick” compensation carried over | `logic_delta=1`, one tick per frame |
| `ld65: BSS overflows by N bytes` | new code in a full RAM area | `#ifndef` dead code, or a hole segment (§4) |
| Random behaviour after boot | stray write into `$9F00-$9FFF` | confine the linker area, check the map |
| `DCL`/`video` does not compile | `struct __vera` has no `video` | `*(volatile unsigned char *)0x9F29` |
| Screen shifted/blank | `DC_VIDEO` missing the layer bit | use `0x51` |
| Keys work but pause reopens every frame | START level-sensitive | make START/SELECT rising-edge |
| Cheat needs frame-perfect timing | comparing held pad to the code | count pad changes |
| Music drifts over time | tempo changed by tick rate | use the 1/256 accumulator |

---

## 14. Work order and budget

| Step | What | Time |
| --- | --- | --- |
| 1 | inventory, toolchain, VERA base, memory map | 1–2 days |
| 2 | KERNAL LOAD asset layer + lower-case names | 3–5 days |
| 3 | boot chain (loader PRG) | 1–2 days |
| 4 | input layer (joystick_get, edge/level) | 2 days |
| 5 | VSYNC IRQ cadence + music tick correction | 3–4 days |
| 6 | memory/ZP tidy-up | 1–2 days |
| 7 | behaviour fixes + simulation harness | 2–4 days |
| 8 | end-to-end verification, screenshots, audio | 3–5 days |
| 9 | browser build, packaging | 2–3 days |

Alter Ego did steps 1–8 in two days because the VERA layer really is 1:1; assume three to four
weeks for a bigger a2vera game.  A game like freegemas will have more asset types and its own
timing assumptions — verify those in step 1 and re-measure, do not copy these numbers.

---

## 15. Where to look in this repository

| Question | File |
| --- | --- |
| What was the plan, in order, with risk items | `x16/docs/PORT-CX16-EVAL.md` |
| Asset layer skeleton, lower-case names, staging | `x16/spike/asset_cx16.c` |
| `jsr $FFD5` wrapper | `x16/spike/kload_cx16.s` |
| Level streaming, VERA address save/restore | `x16/spike/io_cx16.c` |
| Keyboard joystick, key mapping, IRQ counter | `x16/spike/input_cx16.s` |
| Loader and overlay boot | `x16/spike/loader.s`, `loader.cfg` |
| Linker areas, hole segment | `x16/spike/game.cfg` |
| Build script / flags | `x16/spike/build.ps1` |
| One-byte function that did not fit | `x16/spike/gate_cx16.s` |
| Automation, screenshots, wav | `x16/tools/shot.ps1`, `playtest.ps1`, `x16/spike/wavstat.py` |
| Geometry simulation | `x16/spike/fallswap_sim.py` |
| Browser player | `web/x16/assemble.mjs`, `web/x16/app.js` |

---

## Appendix A — pre-flight checklist (copy this into the new port's notes)

```text
[ ] Apple II build still builds, map recorded (CODE/BSS extents, ZP usage)
[ ] All $C0xx / ProDOS / iobuf / keyboard-latch references listed
[ ] VERA features listed (layer0 mode, sprites, PSG, palette, scaling)
[ ] -t cx16 build of main.c has zero errors with -DVERA_BASE=0x9F20
[ ] ca65 sources assemble with --cpu 65C02 and the new base
[ ] game.cfg RAM area fits under $9EFF; map checked; no $9F00 writes
[ ] ZP $9A-$9F (if any) moved into $22-$7F
[ ] asset names lower-cased in the load path; A=0 checked, not carry
[ ] CLRCHN after every load; RAM_BANK restored
[ ] read() saves/restores VERA.address
[ ] loader PRG boots, music overlay lands, jmp works
[ ] keyboard joystick device 0 used; START/SELECT rising-edge
[ ] $C000/$C010 reads gone (or #ifndef'd away)
[ ] IRQ chained to the KERNAL; VERA_IEN never zeroed; frame counter works
[ ] 1.5× compensations removed under VERA_X16
[ ] walking speed matches the NES original
[ ] Apple II build byte-identical (listing diff = 0)
[ ] screenshots of title, level 1, special keys; -Wav audio check
[ ] geometry/behaviour simulation looks right
[ ] browser build assembled and smoke-tested (if shipping it)
```
