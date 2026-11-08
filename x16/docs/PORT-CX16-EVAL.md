# Alter Ego: feasibility of porting the Apple II VERA build back to the Commander X16

- Evaluation date: 2026-11-05
- Subject: this repo's `vera/` (the Alter Ego port for the Apple II + VERA card)
- Target: Commander X16 (65C02S at 8 MHz, 512 KB banked RAM, VERA)
- Toolchain: cc65 2.19's `-t cx16` (`cx16.lib` / `cx16.cfg`)
- Verification environment: `C:\dev\emu\x16emu` (x16emu r49 "Pyrite")
- Artifact directory: `x16/` (this document, `probe/`, `spike/`, `tools/`)

> This document grew from a feasibility study into an implementation record: as of
> 2026-11-06, `x16/spike/dist/` is a complete port that boots, can be played, and has title
> music and SFX (all 26 level files LV00–LV25, the title menu, the in-game pause menu, credits
> and the ending), and the same build also runs in a browser (official WebAssembly emulator +
> GitHub Pages, see §9).  §13 lists the evidence item by item; the only things still unverified
> are the items at the end of §10 and §13 (real hardware, SD/DOS packaging, long hands-on play).
> It makes no claim that "the hardware release is done".
>
> The Traditional Chinese original of this document is
> [`PORT-CX16-EVAL-tw.md`](PORT-CX16-EVAL-tw.md) — same content, translated 2026-11-06.

---

## 1. Summary of conclusions

| Item | Verdict | Basis |
| --- | --- | --- |
| Can the VERA video layer be reused 1:1 | **Yes** | The VERA register offsets are identical on both sides, only the base address differs (`$C200/$C400` → `$9F20`); `L0_CFG/L0_MAP/L0_TIL/HSC/VSC/DC_VIDEO/OAM/PSG` all carry over |
| Does the C source compile as-is | **Yes** | `vera/src/a2vera/main.c` (1760 lines) compiles with `-t cx16 -DVERA_BASE=0x9F20`, zero errors |
| Can the assembly sources be reused | **Mostly** | `title.s`, `oam.s`, `music_api_ftm.s`, `music_imports_ftm.s`, `ftm_sfx_simple.s` all assemble with `-D VERA_BASE=$9F20` |
| Does the memory layout fit | **Yes** | The Apple II build's `$2000-$91FF` body + BSS to `$94B4` + C stack `$94C0-$9600` all fall inside the X16's `$0000-$9EFF` fixed RAM |
| Can it link, produce a PRG and boot | **Verified** | `GAME` (29,698 B), the `MUSIC` overlay (4,097 B) and `LOADER.PRG` (1,026 B) are all produced and x16emu boots to the loader |
| Does the title screen show | **Yes, verified** | Title, menu, starfield and sprites are all correct (`x16/spike/shot-title-final.png`) |
| Do the levels load and play | **Yes, playable** | Level files are stream-compressed through VRAM staging into the map; `HELLO WORLD`, the HUD, bricks, enemies and water are all correct; `Enter` enters a level, the arrows move, `Z` exchanges, `Enter` pauses/resumes, and the title menu can select Level 03 (`x16/spike/play-*.png`, `menu-*.png`) |
| Are all 26 levels in the shipped directory | **Yes (LV00–LV25)** | LV01, LV03 (menu-selected) and LV24 (a vertically mirrored level) were played for real; the rest go through the same `load_level_file()`, without per-level play testing |
| Are the game-feel bugs fixed | **Yes, all three on the X16** | Check the exchange every frame while falling (§7.10), snap the landing to a tile after an exchange (§7.11), and a vertically mirrored level's mirrored spot needs floor (§7.11); the floor-through simulation went 756→0 |
| Playable in a browser | **Yes** | The official X16Community r49 WebAssembly emulator + GitHub Pages (`/x16/index.html`, see §9); headless Edge with `Enter` captured the title screen and Level 1 (`x16/spike/web-title.png`, `x16/spike/web-level1.png`) |
| Overall feasibility | **Feasible, high reuse, medium effort** | Video, audio and input barely need rewriting; the real work is file I/O + the boot chain + cadence correction |

In one sentence: **the VERA layer is almost free; the X16's load path is the only real barrier,
and its root cause turned out to be HostFS wanting lower-case file names (see §7.5).**  `GAME` +
`MUSIC` + `LOADER.PRG` now run in x16emu all the way to the title screen and a playable Level 1
(§7.6, §7.7).

---

## 2. The two platforms compared

| Item | Apple II (+ VERA) | Commander X16 |
| --- | --- | --- |
| CPU | 6502 / 65C02 (1 MHz ~ 1.02 MHz) | 65C02S @ 8 MHz |
| Main RAM | 48–64 KB linear | `$0000-$9EFF` fixed + `$A000-$BFFF` banked (512 KB, bank selected at `$00`) |
| I/O | `$C000-$CFFF` slot space | `$9F00-$9FFF` (VERA owns `$9F20-$9F3F`) |
| VERA base | Slot 2 `$C200` / Slot 4 `$C400` | `$9F20` |
| Video memory | 128 KB VRAM (two banks) | Same, 128 KB |
| Text/BIOS | Applesoft / Monitor ROM | KERNAL + BASIC ROM (with DOS support) |
| File system | ProDOS (MLI, `open/read/close`) | DOS (cmdr-dos) / HostFS, through KERNAL `$FFxx` |
| Interrupts | VERA VSYNC, polled or IRQ | VERA VSYNC + the KERNAL IRQ vector (`$0314/$0315`) |
| Sound | VERA PSG, 16 channels | Same (PSG at `$1F9C0`) |

The point: **the X16's VERA is the same chip a2vera uses (the same register definitions)**, so
drawing, palettes, sprites, scrolling and PSG need no redesign at all — only the base address
changes.

---

## 3. VERA register map (what is actually used)

| Purpose | a2vera macro | Apple II address | X16 address | Same? |
| --- | --- | --- | --- | --- |
| Address low/mid | `VERA_ADDR_L/M` | base+$00/$01 | `$9F20/$9F21` | offset identical |
| Address high (A16 + increment) | `VERA_ADDR_H` | base+$02 | `$9F22` | same |
| Data ports 0/1 | `VERA_DATA0/1` | base+$03/$04 | `$9F23/$9F24` | same |
| Control (DCSEL/ADDRSEL) | `VERA_CTRL` | base+$05 | `$9F25` | same |
| IRQ enable/status | `VERA_IEN/ISR` | base+$06/$07 | `$9F26/$9F27` | same |
| Display mode | `VERA_DC_VID` | base+$29 | `$9F29` | same (`0x51` = VGA+Layer0+sprites) |
| Layer0 config | `VERA_L0_CFG/MAP/TIL` | base+$2C/$2D/$2E | `$9F2C/$9F2D/$9F2E` | same (4bpp `$12`, tile base `$80/$90`) |
| Layer0 scroll | `VERA_HSCROLL/VSCROLL` | base+$2F/$30 | `$9F2F/$9F30` | same |
| Sprites | OAM `$1FC00`, attr | same | same | same |
| PSG | 16 channels `$1F9C0` | same | same | same |
| Palette | `$1FA00` (256×2 B) | same | same | same |

Pitfalls hit during this work:

1. `cx16.h`'s `VERA.address` is only 16 bits, so `VERA.address = 0x10000` is truncated to 0.
   A16 is bit 0 of `address_hi` and the increment is bits 6-4.  The correct form is
   `VERA.address = a & 0xFFFF; VERA.address_hi = 0x10 | ((a >> 16) & 1);`
2. `struct __vera` (cc65's `cx16.h`) **has no `video` field**, so `VERA_DC_VIDEO` has to be
   `*(volatile unsigned char *)0x9F29`.
3. `VERA_DC_VIDEO`'s `0x01` is only the output mode (VGA), not layer 0; `0x51` is what enables
   layer 0.

---

## 4. Source reuse list

### 4.1 Compiles as-is (only the base address changes)

| File | Lines/size | Notes |
| --- | --- | --- |
| `vera/src/a2vera/main.c` | ~1,760 lines | All the game logic, VERA drawing, levels/collision and menus; compiles with `-DVERA_BASE=0x9F20`, zero errors |
| `vera/src/a2vera/oam.c` | — | sprite shadow table |
| `vera/src/a2vera/music.c` + `ftm_player.c` + `ftm_sfx.c` | — | the FamiTone→VERA PSG player |

### 4.2 Needs small changes (`#ifdef VERA_X16` hooks)

| Place | Why | What this round did |
| --- | --- | --- |
| `main.c`'s `load_raw_asset()` | the Apple II build uses `open/read` (ProDOS MLI); the X16 needs KERNAL LOAD | added an `#ifdef VERA_X16` branch that calls `ae_load_raw_asset()` |
| `main.c`'s `wait_frame()` / `vera_sync_init()` | the Apple II build polls the VERA VSYNC status bit; on the X16 the IRQ is owned by the KERNAL | `vera_sync_init()` on the X16 only clears ISR and does not enable `IEN=0x01`; `wait_frame()` still had to be rewritten (see §8) |
| the ZP `$9A-$9F` in `ftm_envelopes.s` | on the X16, `$9D-$A8` is reserved | has to move into `$22-$7F`, and be reserved in the linker config |
| `iobuf.s` (an Apple II-only 1 KB aligned buffer) | not needed on the X16 | simply not linked |

### 4.3 Assembles and works as-is

| File | What it is |
| --- | --- |
| `title.s` | boot initialisation (`c_sp`, `initlib/zerobss/copydata`, VERA init) plus `.incbin`'d title assets |
| `oam.s` | OAM upload |
| `music_api_ftm.s` / `music_imports_ftm.s` | overlay entry points |
| `ftm_sfx_simple.s` | the compact SFX interpreter |

### 4.4 Has to be rewritten

| Item | Why |
| --- | --- |
| `input.s` (Apple II keyboard/PB0/PB1/PDL) | replaced by the X16 KERNAL: `jsr $FF56` (`joystick_get`) plus `$FFE4`/`$FFD2` for the keyboard; `input_cx16.s` was written in this round (16 B/key mapping, see §6) |
| file I/O | Apple II `open/read/close` (ProDOS) → X16 KERNAL `SETNAM/SETLFS/LOAD`; this round wrote `asset_cx16.c` / `io_cx16.c` / `kload_cx16.s` |
| boot chain | `STARTUP.BAS` (BLOAD music + BRUN game) → an X16 `$0801` PRG loader (`loader.s` in this round) |

---

## 5. Memory / ZP migration

The Apple II build's measured layout today (`vera/AGENTS.md`):

```
main image   $2000-$91FF   game code + data
BSS          $6347-$674B   FTMDATA starts at $6750
extra BSS    $8400-$84FC   phase table $8500-$92DB
high BSS     $93A0-$94B4   C stack from $94C0 (lower bound)
I/O buffer   $0C00-$0FFF   (iobuf.s)
music overlay $1000-$1FFF
```

X16 counterpart:

- Fixed RAM `$0000-$9EFF`: everything above fits (highest is `$94B4`; a stack up to `$9600` is
  fine too).
- `$9F00-$9FFF` is I/O and **must never be touched**: this round set `game.cfg`'s RAM area to
  `$2000-$9400` and let `ld65` place the BSS segment explicitly, so nothing strays out of bounds.
- `$A000-$BFFF` is banked RAM (512 KB): usable for staging/caching, but **KERNAL LOAD is not
  guaranteed to be able to write there** (see §7); this round ended up not using it.
- Zero page: on the X16 `$02-$21` are r0-r15 and `$22-$7F` is free; `$80-$9C` is KERNAL/DOS,
  `$9D-$A8` is reserved, `$A9-$D3` is the maths library and `$D4-$FF` is BASIC.  cc65's `cx16.cfg`
  puts ZP at `$22`, size `$5E`, so `ftm_envelopes.s`'s `$9A-$9F` has to move into `$22-$7F`.
- Interrupts: the X16's IRQ is run by the KERNAL (`$0314/$0315`); a VERA IRQ left enabled
  without clearing `ISR` in the handler will hang the machine — which is why this round turned
  `VERA_IEN` off.

---

## 6. Input compared

a2vera's `pad` bits (defined in `main.c`):

```
PAD_A 0x01  PAD_B 0x02  PAD_SELECT 0x04  PAD_START 0x08
PAD_UP 0x10 PAD_DOWN 0x20 PAD_LEFT 0x40 PAD_RIGHT 0x80
```

The X16 side (`x16/spike/input_cx16.s`, settled by measurement on 2026-11-05):

- **`joystick_get` (`$FF56`) device 0 = the KERNAL keyboard joystick, which reports the live
  held state.**  This build uses it as the source for the arrow keys.  It had earlier been
  judged "unusable as a keyboard" because the KERNAL IRQ was off at the time (see the next
  bullet), so its state was simply never updated; with the IRQ fixed it tracks press/release:
  the arrows are level-sensitive (holding keeps walking), and `Enter/Z/X/Shift` map to
  START/B/A/SELECT.
- **The buttons**: `A`/`B` are level-sensitive too (real pads behave that way and the NES treats
  them as "held"; the game itself de-duplicates with `exchange_input_lock`, so they do not
  repeat-fire).  `START`/`SELECT` are the ones that stay rising-edge single-frame pulses,
  otherwise `Enter` would reopen the pause menu every frame.  Only when the keyboard joystick is
  absent (`Y != 0`) does it fall back to key events + `KEY_LOCK`.
- **The arrow keys' "hold timer" was removed** (it is only used when the keyboard joystick is
  missing).  It used to keep running for 8 frames after the key was released, which was one tile
  too far — that is the "I aimed for X but ended up at X+1" bug.  Measured with a beacon
  (`AE_EXTRA_DEFINES='AE_DEBUG_XY'`, printing `player_x` every 10 frames): hold right for 0.25 s
  → x 184→200 (16 px, ending exactly on a tile boundary); before the fix it was 208.
- **Exchanging while falling**: during a fall `check_tile_actions()` only runs once per 8 px
  landing row (`player_fall_steps==0`), so a single-frame pulse has to hit exactly that frame
  (a 1-in-8 chance), which players felt as "I press and nothing happens, I have to mash it".
  With level-sensitive input, holding for 0.1 s or more necessarily covers the check frame.
  Measured `right+z:3` (hold right and Z while walking off a platform edge): HUD `x2`→`x1`, the
  two Egos swap immediately, and holding Z for 3 s costs exactly one exchange
  (`x16/spike/shot-input-exchange-fall.png`).
- Why the old key-event version was not enough: the KERNAL only puts the pressed character into
  the queue, and holding an arrow key depends on the OS/SMC auto-repeat (on x16emu that is
  driven by Windows, with a default delay of about 0.5 s), which produced "tap once, walk one
  tile, wait half a second, then walk continuously".  The keyboard joystick has no such delay,
  which is also why `WASD` was dropped on the X16 (the keyboard joystick has no W mapping, so
  keeping it would only be inconsistent).
- Keys the keyboard joystick does not map still go through key events: `Space` = START and `1` =
  SELECT; `J`/`K` are only A/B fallbacks when the keyboard joystick is absent.
- The special keys `T` (SFX/BGM test), `M`/`N` (mutes) and `ESC` (leave the test) also go through
  key events; details in §7.9.  Neither path needs (or should) read the Apple II's
  `$C000`/`$C010`.
- `game.cfg`'s BSS area has only about 30–40 bytes of headroom left (`BSS` now ends at `$672F`,
  `FTMDATA` starts at `$6750`): any further C code added for the X16 can overflow BSS, so first
  cut Apple II dead code inside `#ifndef VERA_X16`, or adjust the config.
- The SNES pad uses devices 1-4 as documented (`Y=$FF` means not connected).
- **The critical earlier mistake**: the X16 KERNAL's 60 Hz IRQ is sourced from **VERA VSYNC**
  (see §8), so zeroing `VERA_IEN` (which this round did early on, in order to poll `VERA_ISR`)
  stops the KERNAL's IRQ handler entirely → the jiffy clock stops, keyboard scanning stops, and
  `GETIN` always returns 0.  That was the real reason "none of the buttons work"; it had nothing
  to do with how keys were injected.
- Measured (Level 1, `x16/tools/playtest.ps1` sending real scan codes): `Enter` enters the level,
  holding an arrow moves right (about 58–62 px per second, starting on the very first press with
  no stall), `Z` exchanges (HUD `x2`→`x1`), `Enter` brings up RESUME/RESTART/EXIT GAME and
  `Enter` again returns to the game; the title menu's Down/Right/Enter reaches Level 03 "BROKEN
  BRIDGE".  Evidence screenshots `x16/spike/play-*.png`, `x16/spike/menu-*.png`,
  `x16/spike/shot-input-right.png`, `x16/spike/shot-input-exchange-fall.png`.

---

## 7. File loading: the biggest obstacle this round (important)

### 7.1 The facts observed

On x16emu r49 this round ran 20-odd independent probes (`x16/probe/io*.c`, screenshots
`x16/probe/shot-io*.png`) and reached these **reproducible** conclusions:

| Test | Result |
| --- | --- |
| cc65 `open()` (the CBM layer in `cx16.lib`) opening a file on HostFS | **always returns -1** (`io.c`/`io2.c`) |
| streaming a file with `cbm_k_chrin()` | the first call already returns the EOF status `0x42` (`io6`/`io7`), unusable |
| CHRIN after `OPEN 2,8,2,"FOO,S,R"` | the screen goes blank (`io11`), unusable |
| raw KERNAL `jsr $FFD5` (own `kload.s`) | it returns, but **`A=4`, carry is always 1** (`P=31`), and the file contents do not appear at the target address |
| LOAD into VRAM (`A=2` bank0 / `A=3` bank1) | the read-back at the target address does not match the file (`io18`/`io19`) |
| taking a full VRAM mirror with `-dump V` (`Ctrl+S`/`$9FB5` + PC=`$FFFF`) | `dump.bin` contains neither `TILES`' `0x33` block nor `CRPAL`'s `00 00 07 00`, proving the assets did **not** reach VRAM |
| a multi-stage boot chain (`LOADER.PRG` → `LOAD "MUSIC"` → `LOAD "GAME"`) | the `$9FB9` beacon shows the loader advancing ('B'→'M'→'J'), but `$2000` does not hold `GAME`'s first byte (which should be `D8`), so LOAD is not landing |
| a clean HostFS root with only 7 files | same behaviour, ruling out "number of files in the directory / HostFS cache" |

In other words: **x16emu's own `-prg` injection can load files, but the machine's internal KERNAL
LOAD cannot reach HostFS in this configuration** (it returns `A=4`, a timeout/error), so every
asset load came back empty.

### 7.2 Impact

- The title screen, credits and level graphics do not appear (the screen is uninitialised VRAM
  noise).
- This is not a VERA or game-logic problem but the "X16 DOS/HostFS path" problem.

### 7.3 The three suggested routes (in order)

1. **Use DOS's proper load path**: the X16's `LOAD` needs cmdr-dos present.  Use `-sdcard`, or
   `BOOT`/`DOS` into DOS first and then run the loader; or use BASIC's `LOAD`/`BLOAD` (the
   `$FFD5` entry called from BASIC first makes sure DOS channel 15 is ready).  Work out what
   actually triggers HostFS and `-fsroot` in this ROM (r49's IEEE API interception).
2. **Pack with `-sdcard` into a FAT/`.zip` image**: put `TILES/CREDITS/LVxx/*.PSG` on an SD image
   and read them through DOS; this is closest to the real release path and avoids HostFS's
   emulator quirks.
3. **Embed all the assets**: `TILES` (16 KB) + title/credits (4 KB each) + palettes (512 B) is
   about 25 KB, which can go straight into `GAME` via `.incbin`; only the 26 level files (~2.7 KB
   each) stay on disk and load at runtime.  Embedding makes "the title screen appears at boot"
   independent of file I/O, and is the fastest demonstration path.

### 7.4 Correct usage that holds whichever route you take

- **The carry returned by `LOAD` is not trustworthy**: every successful LOAD in this round also
  reported `P=31` (carry=1).  Do not use `bcs fail` to decide success (the loader here once
  jumped straight to fail because of it).
- `SA=1` (with a 2-byte header) uses the header's address; `SA=2` (no header) uses X/Y.  Both
  failed under this round's HostFS, but the API usage itself is right.
- A target address of `$0000` (a2vera's `GOVER`/`ENDING` use `address==0`) is not accepted by
  KERNAL LOAD; it has to be loaded to a staging area and then copied.

---

### 7.5 Conclusion (root cause found: file-name case)

Later measurements overturned §7.1's conclusion: **the problem was neither DOS/HostFS nor the way
LOAD was called, but the file-name characters sent through `SETNAM`**.  x16emu r49's HostFS only
recognises **lower-case ASCII file names**:

| Name sent | LOAD returns | Target address |
| --- | --- | --- |
| `"GAME"` (upper-case ASCII) | `A=4` (FILE NOT FOUND) | not written |
| `"game"` (lower-case ASCII) | `A=0` (success) | `$2000` = `D8` (the correct first byte) |

Verification (`x16/spike/t3.s`, `t5.s`, beacon printed via `$9FB9`):

- `LOAD "music"` → `$1000` = `20` ✓, `LOAD "game"` → `$2000`=`D8`, `$2001`=`A2` ✓.
- after `LOAD "tiles"` (SA=2, A=3, addr 0), VRAM `$10000+$20` reads back `02 22 22 20`, **exactly
  the same** as the host's `vera/build/stage/TILES[32..35]` ✓.
- after `LOAD "crpal"` (SA=2, A=3, `$FA00`), VRAM `$1FA00` reads back `00 00 07 00 5D 00`, **exactly
  the same** as the host's `CRPAL[0..5]` ✓ (the earlier "off by one byte" was a misreading).
- so §7.1's "assets never land" observations were caused purely by the upper-case names; the
  missing data in `-dump V`'s `dump.bin` had the same cause.

**The fix**: every `SETNAM` name becomes lower case (`loader.s` uses `"music"`/`"game"`;
`asset_cx16.c`/`io_cx16.c` must convert `A-Z` to `a-z` before sending the name; the level files
`LV00` → `lv00`).  Also, **the carry returned by `LOAD` is still untrustworthy** (it is `P=31`
even on success), so do not use it to decide success.

### 7.6 The title screen and Level 1 both render (this section is closed)

The "interlaced black stripes" were later confirmed to be a side effect of §7.5's file-name case:
with no assets landing, `title.s` could only draw from leftover VRAM, which looked like stripes.
After lower-casing the names, the title screen (`ALTER EGO`, the menu, the starfield, sprites;
`x16/spike/shot-title-final.png`) and Level 1 (`HELLO WORLD`, HUD `5`/`x2`, bricks, ladders,
enemies, water; `x16/spike/shot-level1-plays.png`) are completely correct, and there is no need to
go back over the `DC_*`/`L0_*` values.  The suspected `DC_HSCALE/VSCALE=$40` (2× scaling) is in
fact the right setting on the X16, and `t7.s`'s "filled a solid colour but saw noise" was because
the asset/map writes were being clobbered by `read()` (see the next section).

### 7.7 Two genuine porting bugs found while entering a level (fixed)

1. **`read()` clobbered the VERA address** (`x16/spike/io_cx16.c`).  The level file is streamed
   byte-by-byte from VRAM staging at `$A000`, but `load_level_file()` writes the map to
   `VERA_DATA0` at the same time; `read()` reset `VERA.address(_hi)` on every byte, so the map was
   written into the staging area, the level data overwrote itself, `load_level_file()` returned 0
   and the screen stayed black (the beacon trace shows no progress after `'L'`, and nothing after
   `'o'`/`'O'`).  Fix: `read()` saves `VERA.address`/`address_hi` on entry and restores them on
   exit (3 bytes in total).
2. **`keyboard_pad()` read the Apple II's `$C000`/`$C010`** (`vera/src/a2vera/main.c`).  The X16 has
   no keyboard latch: `$C000` is ROM and returns a fixed byte, which becomes "a direction is
   permanently held".  An `#ifdef VERA_X16` branch now returns `joystick_pad()` directly
   (`input_cx16.s` already merges the KERNAL keyboard joystick with the SNES pad); the Apple II
   path is completely unchanged.

Also, for automated screenshots, `main.c` gained an `#ifdef AE_X16_AUTOSTART` test hook that only
exists when built with `-DAE_X16_AUTOSTART=<level>`, to skip the menu and enter a level directly.
(Automation can send keys directly now, see §12; the hook is kept but normal builds do not contain
it.)

### 7.8 The boot credits' platform line becomes X16

The cold-boot credits are the original NES nametable (`src/credits.h`) converted to a VERA tilemap
by `vera/tools/a2vera_art.py`; the Apple II build overlays `APPLE II VERA CONVERSION BY` /
`ANOMIXER 2026` on rows 24/26.  The X16 build needs the platform line to read
`COMMANDER X16 CONVERSION BY`, done as follows:

- `a2vera_art.py` gained `AE2VERA_CREDITS_PLATFORM` (default `APPLE II VERA`, so Apple II output
  stays byte-identical) and `AE2VERA_ART_OUT` (output directory), plus
  `python a2vera_art.py credits` to regenerate only the credits.
- `x16/spike/build.ps1` regenerates the credits into `x16/spike/work/art/` after copying
  `vera/build/stage/*`, then overwrites `dist/CREDITS` and `dist/CRPAL`.
- Verification: `x16/spike/shot-credits-x16.png` is x16emu's actual boot screen; the original five
  credit lines other than `Nintendo` are intact, and the last two lines are
  `COMMANDER X16 CONVERSION BY` (blue) and `ANOMIXER 2026` (orange).

### 7.9 Special keys (T/M/N, cow level, level-skip cheat)

Besides the directions and A/B, the Apple II build's `keyboard_pad()` has several keys that are
not pad buttons: `T` directly synthesises the NES's START+A+B to open the SFX/BGM test screen,
`M`/`N` toggle the music/SFX mutes, `ESC` leaves the test screen and `G` re-detects the pad.
There are also two cheats: SELECT on the title screen enters the cow level (`current_level=0`),
and B, left, A, B, left, A followed by SELECT clears the level.  The X16 build wires them all up
but does **not** read the Apple II's `$C000`/`$C010` (that region is ROM on the X16):

- `x16/spike/input_cx16.s`'s `mapkey` recognises `T`/`t` (`$54`/`$D4`), `ESC` (`$1B`), `M`
  (`$4D`/`$CD`) and `N` (`$4E`/`$CE`) and sets a single-frame flag `_ae_key_t`/`_ae_key_m`/
  `_ae_key_n` (cleared at the start of every `_joystick_pad`); `T`/`ESC` additionally push
  START|A|B into `pad` through `set_btn`, keeping the "press T on the title for the test screen"
  semantics identical to the Apple II build.
- `vera/src/a2vera/main.c`: the `VERA_X16` branch's `keyboard_pad()` uses those three flags for the
  mute toggles (including `title_menu_dirty=1`, so the title's MUSIC/SOUND text updates);
  `sound_test_screen()` clears `ae_key_t` on entry and leaves when it sees `ae_key_t` (so pressing
  T to enter and T or ESC to leave always works, and you cannot get stuck in the test screen).
- The Apple II-only `KEYBOARD`/`KBDSTRB`/`keyboard_model` blocks now all live inside
  `#ifndef VERA_X16` (they are dead code on the X16, and keeping them not only wasted space but
  once made the test screen unescapable).

**The cheat's X16-specific adjustment**: A/B are level-sensitive on the X16 (held is held), so
comparing `if (pad == code[i])` every frame as the Apple II/NES does would fail on the second frame
of the same hold and reset the index → in practice the input had to be frame-exact.  The X16 build
counts "**a change in the pad value counts once**" instead (`#ifdef VERA_X16`,
`static code_last_pad`), so tapping at a normal speed works; measured: `z,left,x,z,left,x` then
`1` inside a level shows `LEVEL CLEAR` (`x16/spike/shot-level-skip.png`).

**Measurements** (all x16emu r49 + `x16/tools/playtest.ps1` with real scan codes):

| File | Content |
| --- | --- |
| `x16/spike/shot-soundtest.png` | pressing `T` on the title opens `SFX 00 BGM 1`, right switches to BGM mode (orange text), no leftover text below |
| `x16/spike/shot-mute-keys.png` | pressing `M` then `N` leaves the title showing `MUSIC OFF` + `SOUND OFF` |
| `x16/spike/shot-cow-level.png` | on the title `1` (SELECT) → `Enter` → loads `COW LEVEL` (level 0) |
| `x16/spike/shot-level-skip.png` | cheat `z,left,x,z,left,x` + `Enter` into a level → `1` → `LEVEL CLEAR` |

Audio was additionally checked objectively with x16emu's `-wav` and `x16/spike/wavstat.py` (which
patches the header of the force-killed wav first, then prints RMS/peak per segment).  Title music
is rms ≈ 0.08–0.11 per second; after pressing `T` the title music stops (rms 0.005); in SFX mode
`Z` gives a short burst (250 ms window: rms 0.09, peak 0.105); switching to BGM mode and pressing
`Z` returns to a sustained rms ≈ 0.10.  So the test screen's SFX and music really do produce
output, not just pixels that look right.

### 7.10 Exchanging while falling: from "1 in 8 frames" to "every frame" (added 2026-11-05)

A player reported "while falling, mashing `z` or `x` only exchanges after 3–4 body heights".  The
cause was not the input layer (A/B were already level-sensitive; measured: holding `Z` for a
second gives 61 consecutive frames of `pad=0x02`), but **when the exchange is checked**:

- The NES original checks the exchange inside the `player_dir==DIR_NONE` branch
  (`src/game.c` 1176–1268).  A falling step is `player_move_cnt=8`, and during a fall
  `player_dir=DIR_DOWN`, so **only one frame out of every 8 px** reaches that code → a one-frame
  window.
- The X16 build copied that, and `check_tile_actions(pad)` is likewise only called when
  `player_fall_steps==0`.  Holding the button always catches the window, but a tap only hits it
  1/8 of the time, so even mashing often did nothing and it took 3–4 rows (24–32 px) on average.
- The Apple II build never felt this bad because `$C010`'s any-key-down flag (level-sensitive)
  happens to cover that frame — which also explains why the problem was only reported on the X16.

Fix (`vera/src/a2vera/main.c`, `#ifdef VERA_X16`, not compiled for the Apple II):

```c
if (player_fall_steps && !exchange_active && !player_dead &&
    items_left && (pad&(PAD_A|PAD_B)) && !exchange_input_lock) {
    begin_player_exchange();
    collected=1;
}
```

Every frame of a fall now accepts A/B, and the first frame of the press starts the exchange
animation (the exchange partner is the mirrored Ego, so `y` does not change and only `x` swaps
back and forth); there is no need to wait for the next row.  The `main.c` built for the Apple II is
completely unchanged (only the new code is inside `#ifdef`), and the Apple II artifacts' bytes are
unchanged.

**Measurement**: a build with `$env:AE_EXTRA_DEFINES='AE_DEBUG_FALL'` writes
`(player_y&$F8)|(pad&$07)` to `$9FB9` every frame of the game loop (x16emu's `User debug 1`),
decoded by `x16/spike/bytrace.py`.  Writing 3 bytes per frame (`AE_DEBUG_XY`) occasionally gets
dropped in x16emu, so when frame-by-frame alignment matters use the 1-byte `AE_DEBUG_FALL`.

| Test (`playtest.ps1`) | After the fix |
| --- | --- |
| `enter,right:0.7,z:0.3` | the very first sample with `Z` held is a falling row (`y=144`), and `y` freezes immediately afterwards (the exchange animation starts); the HUD goes `x2` → `x1` (`x16/spike/ma-3-z.png`, `fx-3-z.png`) |
| `enter,right:0.7,x:0.3` | `X` (the A button, `pad=0x01`) also triggers on the first frame (`x16/spike/mb-3-x.png`) |

### 7.11 No falling through the floor after a mid-air exchange: snap the landing to a tile (added 2026-11-06)

After §7.10 shipped, a player reported "sometimes it falls through the ground" (the attached
screenshot was LV24 ALMOST THERE, HUD `x5`/`x5`, at the moment of a fall).  The root cause is that
the exchange animation **freezes the fall between 8 px rows**:

- On the frame A/B is pressed, `player_y` is "the row the fall started in + `r`" (`r=1..7`), while
  `player_fall_steps` still holds `8-r` steps.  `y` does not move during the animation, and when
  it ends `update_player_fall()` sees a non-zero step count and **keeps falling straight away**,
  skipping the floor test in the mirrored column.
- If the next row in the mirrored column is a solid tile, the hero sinks into it; gravity only
  looks at the tile under the feet (`y+8` = the row below the solid tile = empty), decides "no
  floor" → keeps falling → straight through the platform.
- Exchanging while standing does not have this problem (`player_fall_steps==0` and `y` is always
  on a row); only the "accept A/B every frame while falling" added on 2026-11-05 can hit it.

Fix (`main.c`, `#ifdef VERA_X16`, not compiled for the Apple II): when an exchange starts during a
fall, record `exchange_midair`, and when the animation reaches the landing spot snap `y` back to
the row the fall was in and clear the unused steps, so gravity re-tests the mirrored column (it
stops if there is floor, and only keeps falling if there is not).

```c
if (ae_midair_ok()) begin_player_exchange();  /* the trigger */
if (exchange_active) exchange_midair=1;

#ifdef VERA_X16                                 /* advance_player_exchange() */
if (exchange_midair) {
    exchange_midair=0;
    player_y=(uint8_t)(player_y&0xF8);
    player_fall_steps=0;
}
#endif
```

The other half of the cause is the **vertically mirrored levels** (`sync_type!=0`: LV05/08/15/19/24,
five levels): the second Ego is at `y=240-player_y`, so a mid-air exchange teleports the hero
"through the platform" to the mirrored height.  The LV24 screenshot the player attached (HUD
`x5`/`x5`, hero hanging under the main platform) is exactly this: pressing `z` while falling above
the main platform mirrors onto the spot below the platform, and the exchange animation delivers
the hero under the floor.  The geometry (`fallswap_sim.py`): before the fix these five levels
accepted 14,616 mid-air exchanges, and **13,538 of them (93%)** had no floor under the landing
spot.

The fix: in these five levels a mid-air exchange additionally requires "the mirrored spot has floor
under it" (`ae_midair_ok()`); if the mirrored height happens to be a legal landing spot it swaps
immediately, otherwise it waits for the frame where it falls onto a landing spot; 1,694 falling
frames are accepted in total, with 0 floor-through cases.

The C version of the test is about 38 bytes, but only 6 bytes of main RAM were left, so it is
hand-written assembly in a new `GATE` segment:

- `x16/spike/gate_cx16.s`: `uint8_t __fastcall__ ae_midair_ok(void)` returns 1 immediately when
  `sync_type==0`; otherwise it checks `collision_map[((feet-48)>>3)*32+(x>>3)]` for
  `TILE_WALL|TILE_LADDER|TILE_BRIDGE`, with `feet = clamp(240-y)+8` and `feet>=208` treated as a
  wall.
- `x16/spike/game.cfg`: `GATE: load = RAM, type = ro, start = $92DC;`, which fits exactly in the
  hole between `FTMTABLE`'s end `$92DB` and `FTM_HIGH_BSS`'s start `$93A0` (196 bytes; measured 95
  bytes).  `loader.s` loads the whole `GAME` image (`fill = yes` padding is written to the file
  too), so this code is still loaded to `$92DC`.
- `main.c` only has to drop `static` from `player_x`/`player_y`/`sync_type`/`collision_map` (same
  size, no effect on the Apple II build) so that the assembly can import them.

**The Apple II VERA build stays as it was**: all of this round's behaviour changes (checking the
mid-air exchange every frame, snapping the landing to a tile, the mirrored spot needing floor) are
inside `#ifdef VERA_X16`, and `vera/`'s release images do not move.  The Apple II build never had
these two bugs: its exchange only happens on a landing row (`player_fall_steps==0`), the start is
always on a row and no unused steps are left to keep falling in the mirrored column, and it has no
instant teleport in vertically mirrored levels.  Removing `static` was verified harmless for the
Apple II: compiling "the static version" and the current version separately with cc65
`-t apple2 --cpu 6502 -Oirs` gives 6,166 instructions with 0 differences (the listing only gains 4
`.export`s).

**Verification**: `x16/spike/fallswap_sim.py` reads the packets in `dist/LV00..LV25` directly,
rebuilds the collision map and replays `check_map()`/`update_player_fall()`/
`advance_player_exchange()`:

| Build | Fall + A situations | Hero tile turned solid (= floor-through) |
| --- | --- | --- |
| before the fix | 65,667 | **756** (e.g. LV00 `x=104,y0=96` → mirrored `x=144`, landing `(144,104)`) |
| after the fix | 65,667 | **0** (including `sync_type!=0` levels: no exchange when the landing spot has no floor) |

Measured in x16emu (shipped build): LV01 `enter,right:0.7,z:0.3` stands on the ground after the
exchange, the count `x2`→`x1` (`x16/spike/g1-3-z.png`); LV24 (`sync_type=1` vertical mirror, level
24 selected in the menu, then `right:1.2,z:0.4`, pressing `z` when falling at the main-platform
height) gives `x6`→`x5` and the hero **standing on the main platform** (`x16/spike/g24-27-z.png`),
no longer sent underneath it.

## 8. Frame cadence and music

| Item | Apple II build | X16 implementation |
| --- | --- | --- |
| per-frame sync | `while (!(VERA_ISR & 1)); VERA_ISR = 1;` (the VSYNC status bit) | hook `$0314/$0315` to intercept the KERNAL IRQ: the handler only `inc`s a counter and `jmp`s back to the original handler; `wait_frame()` waits for the counter to change (`input_cx16.s` + `main.c`'s `VERA_X16` branch) |
| music tick | synchronised with frames | one FamiTone source tick per frame (`VERA_X16` overrides the Apple II's 1.5-tick schedule) |
| PSG output | VERA PSG, 16 channels | exactly the same (`$1F9C0`) |

**The key point (the original judgement was the opposite; corrected by measurement on
2026-11-05)**: the X16 KERNAL's entire IRQ (jiffy clock + keyboard scan) is driven by the **VERA
VSYNC interrupt** (the KERNAL sets `VERA_IEN` bit 0 = 1 at boot).  So:

- Do not zero `VERA_IEN` to poll `VERA_ISR` — that stops the KERNAL IRQ entirely, the jiffy stops
  and the keyboard queue is always empty (measured: the `$A2` jiffy low byte stayed `$00`
  throughout the game, and the self-installed IRQ counter stayed 0 for 12 seconds).  This is
  exactly why "none of the buttons work" at the start of this round.
- There is also no need to clear `VERA_ISR` in the handler: the KERNAL's handler deals with VSYNC
  itself; our handler only counts and then tail-calls the original.
- On the X16, `vera_sync_init()` becomes `VERA_ISR=0x0F; VERA_IEN=0x01;` followed by a call to
  `ae_irq_install()`; the Apple II path is unchanged.
- Similarly, `asset_cx16.c` does `sei`/`cli` and saves/restores `VERA_IEN` around the KERNAL LOAD;
  after loading it calls `CLRCHN` (`$FFCC`) to give the input channel back to the keyboard,
  otherwise `GETIN` still points at the file.

**Speed correction (2026-11-05, after a player reported "the music is a bit fast, and the game is
a bit fast too")**: the Apple II FTM build only runs about 40 loops a second, so `main.c` scales the
game to 60 Hz with `logic_delta=(++ftm_rate_phase&1)?2:1` (1.5 NES steps per loop on average) and
`ftm_player.c`'s `music_tick_impl()` alternates 1/2 source ticks for level songs (1.5 on average).
The X16 loop is already VSYNC-locked at 60 per second (measured: not one VSYNC skipped), so
applying those two 1.5× compensations makes **everything 1.5× too fast**: the hero walks ≈90 px per
second (the NES does 60 px) and the level music is 50% fast.  Fix: both places take a single-step
path under `#ifdef VERA_X16` (`logic_delta=1`, exactly 1 source tick per frame), while the Apple II
build keeps its compensation.  Measured after the fix: 235→347 px over 2 seconds (≈56 px/s),
matching the NES's 60 px/s.

**Music tempo trim (2026-11-05, after a player reported "the music is a tiny bit slow")**: this X16
build is at the NES's native 60 source ticks/s, but the player still felt it slightly slow.  So
`AE_X16_TEMPO_TRIM` was added (units of 1/256 tick/frame, default 8 ≈ +3.1%, 0 = exactly 60 Hz):
`music_tick_impl()` uses an 8-bit accumulator that fires one extra tick when it wraps 256, so there
is no long-term drift.  The Apple II path is unaffected; override it at build time with
`$env:AE_X16_TEMPO_TRIM`.

**Pause-menu cues: EXIT GAME was silent, RESTART droned (2026-11-08, reported on the X16 build
and on the Apple II VERA build, which share this `main.c`)**.  Two independent faults in one path:

- EXIT GAME played no cue at all: the pause-confirm branch jumped straight to
  `leave_game_to_title()` and only the RESUME/RESTART paths reached `sfx_start(0)` (NES: every
  pause confirm plays `SFX_START`).  Fixed by starting the cue before the branch.
- RESTART left a drawn-out tone.  The confirm cue is `SFX_START` = 83 SFX source ticks ≈ 1.38 s
  (`vera/build/ftm_sfx_data.s`).  Two separate things kept a note sounding after the confirm:
  1. `loading_tick()` returned early whenever `active_music==255` — the exact state
     `stop_music()` leaves behind for a restart level read.  Music tick and SFX tick were both
     skipped for the whole read, so on the Apple II builds the SFX stream stopped advancing and
     the PSG voices simply held the note they had reached.  Fixed by ticking SFX on every VSYNC
     in `loading_tick()` (music stays gated, or the FTM player would resume its disk prefetch in
     the middle of the read).
  2. The X16 asset layer has a worse variant that `loading_tick()` cannot reach: `open()` stages
     the *whole* level file into VRAM with one KERNAL LOAD under `sei` (`x16/spike/asset_cx16.c`,
     `ae_stage_vram()`), so there is no point inside the transfer where anything can tick.  On
     this build the cue's current note was therefore held for the entire staging read — about
     half a second to a second on HostFS and longer on a real SD card — and was only released by
     the `sfx_stop()` that ran *after* the load: the drawn-out tail reported for the X16.
     Fixed by stopping the pending cue at the top of `load_level_file()` under `#ifdef VERA_X16`,
     i.e. exactly where the ticking stops.  The confirm cue is now heard for the 16-frame fade
     (≈0.27 s), the staging read is silent, and the level theme starts on the next line.

Cutting the cue needed a stop that the music API did not have: `sfx_stop()` (clear the stream
pointer and repeat counter, then silence the four SFX voices).  FTM: `_ftm_sfx_stop` in
`vera/src/a2vera/ftm_sfx_simple.s`, aliased in `music_imports_ftm.s`.  PSG: `sfx_stop_impl()` in
`music.c`, reached through the overlay at `$1027` (`_sfx_stop` in `music_api.s` /
`music_imports.s`; it is the tenth entry after `_music_prefetch` at `$1024`, so no existing
address moved).  The Apple II builds call it after the level read (their 640-byte chunked ProDOS
reads keep ticking, so the cue really does play through the load) and the X16 build calls it
before the read; either way it is cut before `play_music()`, i.e. where the level theme begins.
EXIT GAME starts the cue before the transition and cuts it at the title music.

Fitting it cost memory.  `#ifdef FTM_VERA` covers the X16 build and the Apple II FTM build, and
the extra code pushed ONCE past the `$6750` FTM data base — X16 BSS overflowed by 5 bytes.
Seven bytes of cold state (X16 eight, `VERA_X16` adds `exchange_midair`) moved out of the main
BSS into `FTM_HIGH_BSS` via `#pragma bss-name`: `level_fade_frame`, `bridge_dropped`, the three
exchange words, `exchange_input_lock` (+ `exchange_midair` on the X16).  New maps: X16 BSS
`$62F6-$674C`, `FTM_HIGH_BSS` `$93A0-$94BC` (stack lower bound `$94C0`), FTMDATA still `$6750`
— 3 bytes spare each side; Apple II FTM BSS ends `$674F`, high BSS ends `$94BB`.

Evidence: `vera/build/shots/x16_pause_restart.wav` (re-recorded after the blocking-load fix: the
confirm cue runs only for the fade, the staging read is digital silence, then the level theme)
and `x16_pause_exit.wav` (confirm cue in the fade, then the title screen); the matching
screenshots showed the pause menu on RESTART, HUD `x4` after the restart and the title after
EXIT GAME.  Both `vera/build` images were rebuilt after the change (the Apple II binaries are
unchanged: the new stop is X16-only).

Reading a `-Wav` capture of this build: a plateau of two or three sample values at a fixed
amplitude is a *held* PSG voice, not a recording artefact — the PSG runs autonomously, so a voice
whose gain is not rewritten simply keeps sounding.  That is what made the pre-fix capture look
like "one second of silence": it was neither silence nor music, it was the frozen cue note.
Long silent gaps during a staged LOAD, by contrast, really are silent (verified with SOUND
muted).  `playtest.ps1 -TailSeconds <n>` keeps the emulator running after the last key so a
recording actually reaches the new level.

The browser player (§9, release form 3) runs this same binary, so the RESTART fix is in it with
no separate change — its emulated HostFS read is faster than a HostFS/SD read, so the frozen note
used to be shorter there, but it is cut at the same point now.

---

## 9. Packaging and releases

The X16 has three release forms:

1. **A multi-file directory / HostFS**: `LOADER.PRG` + `GAME` + `MUSIC` + the asset files.  Easiest
   during development (`-fsroot`) and **working now** (file names must be lower case, see §7.5).
2. **A `.zip`/SD image (AutoBoot)**: pack the above into an SD card image and the X16 loads
   `AUTOBOOT.X16` at boot.  This is the hardware release form.
3. **Browser (GitHub Pages)**: the same `dist/` on the official X16Community r49 WebAssembly
   emulator (`x16emu_wasm-r49.zip`, pinned with SHA-256).  `web/x16/assemble.mjs` downloads the
   release when the site is built, copies the assets under **lower-case names** plus a
   `manifest.json` into `x16/game/`; `web/x16/app.js` then `FS.writeFile`s every file into the
   emulator's virtual drive `/` and starts `-prg loader.prg -run`.  The page is at
   `/x16/index.html`; `x16emu.data` contains the X16 ROM, so `web/x16/` also ships
   `emulator-license.txt` / `rom-license.md` / `NOTICE.md`.

Suggested release names follow `vera/`'s `alter-ego-vera*` convention (e.g. `alter-ego-x16.prg` +
`alter-ego-x16.zip`), without renaming any existing release.

Release form 3 is not a fork of the build: it ships `x16/spike/dist/` verbatim, and
`.github/workflows/deploy-web.yml` triggers on `x16/spike/dist/**`, so any X16 fix that lands a
rebuilt `GAME` is redeployed automatically.  Do not assume that, though — check the deployed
binary, because the site renames files to lower case:

```powershell
Invoke-WebRequest https://anomixer.github.io/alter-ego/x16/game/game -OutFile tmp\web-game
(Get-FileHash x16\spike\dist\GAME).Hash -eq (Get-FileHash tmp\web-game).Hash
```

Verified for `feb4c1b` (the RESTART-cue fix): workflow run `42466205760` succeeded and the
deployed `x16/game/game` hashes to `0398F06A…0B65`, identical to the local `GAME`.


---

## 10. Risk list

| Risk | Status (2026-11-06) |
| --- | --- |
| HostFS/DOS load path (§7) | **Resolved**: lower-case names suffice (§7.5); `-sdcard`/DOS boot not yet tested |
| ZP `$9A-$9F` conflict | **Still open**: the 4 bytes in `ftm_envelopes.s` are still at `$9A-$9F` (BASIC's ZP on the X16); it has not bitten yet, but it is a latent bug — move it to `$22-$7F` before going to hardware |
| Interrupt storm | **Resolved**: `VERA_IEN=0x01` plus a handler chained onto the KERNAL's `$0314` (see the paragraph before §7.7) |
| Cadence (60 Hz emulation vs 8 MHz) | **Resolved**: VSYNC IRQ frame counter, `logic_delta=1`, one music tick per frame (§8) |
| Straying into `$9F00-$9FFF` | **Resolved**: the config confines it to `$2000-$9400`, and every build checks the map |
| Asset formats | No risk: the VERA 4bpp tile/palette binaries are the same as the Apple II build's, copied straight over |
| Memory | **High**: only 3 bytes of main RAM left (CODE `$5A72` / BSS `$674C`), so new features first need a hole or dead code cut (see "Memory headroom" in `x16/README.md`) |

---

## 11. Effort estimate (one person)

| Phase | Content | Estimate |
| --- | --- | --- |
| A. Get file I/O working | DOS/HostFS or an SD image, so assets load | 3–5 days |
| B. Asset layer | `ae_load_raw_asset` / level stream (including `address==0` and bank1) | 2–3 days |
| C. Input | the `input_cx16.s` mapping, keyboard/pad measurements | 2 days |
| D. Cadence and music | IRQ frame counter, FTM tick correction, SFX | 3–4 days |
| E. Memory/ZP tidying | ZP move, config convergence, map checking | 1–2 days |
| F. Verification and packaging | title→level→ending end to end, the SD image | 3–5 days |
| **Total** | | **about 3–4 weeks (one person, part time maybe 1.5–2 months)** |

**Actual result**: A–F were done in two days (2026-11-05/06), not counting hardware and SD image
packaging, mainly because the file-I/O root cause was just file-name case and the VERA layer really
is 1:1.  What remains is §10's latent ZP bug and long hands-on play.

For comparison: `time-pilot`'s CX16→Apple II VERA port shared no HAL, which amounted to rewriting
`main.c`, about one person-month; this project's `main.c` was already cc65 and its VERA layer is
1:1, so reuse is clearly higher and the main cost is platform differences (file I/O, input,
interrupts) rather than game logic.

---

## 12. Verification plan (steps that can be run)

1. `powershell -NoProfile -File x16\spike\build.ps1` → produces `dist\GAME`, `dist\MUSIC`,
   `dist\LOADER.PRG`, `dist\*.PSG`, `dist\LVxx`.
2. `x16emu -prg x16\spike\dist\LOADER.PRG -run -fsroot x16\spike\dist` (add `-warp` to speed it up)
   → watch whether the loader reaches `jmp $2000`.
3. The `$9FB9` beacon: `User debug 1: $xx` is printed on the emulator console and works as a
   progress lamp (this round used it to trace the loader's 'B'/'M'/'J' and the asset layer's
   'A'/'V').
4. VRAM content check: `-dump V` + `$9FB5=1` + jump to `$FFFF` produces `dump.bin` (128 KB VRAM +
   composer + palette + layer registers), which can be compared offline against `TILES`/`CRPAL`.
5. Screenshots: `x16/tools/shot.ps1 -Prg ... -FsRoot ... -Out ...png` (foreground capture; the
   emulator does not have to cooperate).
6. Key automation: `x16/tools/playtest.ps1 -KeySequence 'enter,right:2,z,enter'`.
   **Synthetic keys only reach the guest with real scan codes**:
   `keybd_event(vk, MapVirtualKey(vk,0), flags)`; arrow keys additionally need
   `KEYEVENTF_EXTENDEDKEY` (flags=1 for down, flags|2 for up).  This is also why it was wrongly
   concluded early on that "x16emu ignores synthetic keys" (`SendKeys`/`SendMessage` carry no scan
   code).  The available key names include `t`/`m`/`n`/`one`/`esc` (§7.9's special keys);
   `-Wav <file.wav>` makes x16emu record, after which
   `python x16/spike/wavstat.py <file.wav> [window seconds]` prints RMS/peak per segment (the
   script force-kills, so the wav header is unfinished and `wavstat.py` patches it first).  Note:
   playtest's `try/finally` always closes the emulator, otherwise its redirected stdout makes the
   caller look stuck.
7. Level-clear verification: load `LV00`…`LV25` and confirm `load_level_file()`'s 2 B header, 512 B
   collision map, 3 B per entity, and 3 B parameters + 640 B collision map all match the Apple II
   build.

---

## 13. Measured results (the evidence this round leaves behind)

| File | Content |
| --- | --- |
| `x16/probe/main.c` | basic VERA tests (display mode, palette, tiles) |
| `x16/probe/io*.c` | 20+ file-API / LOAD behaviour probes |
| `x16/probe/shot-io13.png`, `shot-io18.png`, `shot-io19.png`, `shot-io20.png` | screen evidence of LOAD/VERA address behaviour (including the palette values from `read`/`read2`) |
| `x16/probe/shot-io6.png`, `shot-io7.png`, `shot-io11.png` | evidence of CHRIN streaming failure (status `0x42`, blank screen) |
| `x16/spike/` | the complete cc65 `-t cx16` build: `GAME` 29,698 B, `MUSIC` 4,097 B, `LOADER.PRG` 1,026 B |
| `x16/spike/shot-title-final.png` | the title screen on the X16 (`ALTER EGO` + four menu rows + starfield) |
| `x16/spike/shot-level1-plays.png` | Level 1 on the X16 (`HELLO WORLD`, HUD `5`/`x2`, bricks, enemies, water) |
| `x16/spike/play-1-enter.png` … `play-5-enter.png` | an actual play sequence: enter the level → hold right for 2 s → `Z` exchange (HUD `x2`→`x1`) → `Enter` pause (RESUME/RESTART/EXIT GAME) → `Enter` resume |
| `x16/spike/menu-1-down.png` … `menu-5-enter.png` | title menu Down/Right selects START LEVEL 03 → `Enter` loads "BROKEN BRIDGE" |
| `x16/spike/shot-credits-x16.png` | boot credits: the last two lines are `COMMANDER X16 CONVERSION BY` / `ANOMIXER 2026` (§7.8) |
| `x16/spike/shot-input-right.png` | holding an arrow moves (continuous while held, no stall after the 8th frame) |
| `x16/spike/shot-input-exchange-fall.png` | `right+z:3`: exchanging while walking off a platform edge, HUD `x2`→`x1`, the two Egos swap, and holding Z for 3 s costs one exchange |
| `x16/spike/ma-3-z.png`, `fx-3-z.png` | after the §7.10 fix: pressing `Z` while falling starts the exchange on the first frame (HUD `x2`→`x1`) |
| `x16/spike/mb-3-x.png` | the same fall using `X` (the A button) also exchanges on the first frame |
| `x16/spike/g1-3-z.png` | after the §7.11 fix (shipped build): LV01, `Z` while falling, standing on the ground afterwards (HUD `x2`→`x1`) |
| `x16/spike/g24-27-z.png` | after the §7.11 fix: LV24 (vertical mirror), `Z` while falling at the main-platform height, hero standing on the main platform (HUD `x6`→`x5`) |
| `x16/spike/fallswap_sim.py` | rebuilds the collision map from `dist/LVxx` and replays fall/exchange geometry: 756 of 65,667 situations sank into a tile before the fix, 0 after |
| `x16/spike/gate_cx16.s` | `ae_midair_ok()`, which would not fit in the main RAM area (the `GATE` segment at `$92DC`, see §7.11) |
| `web/x16/`, `web/x16/assemble.mjs` | the browser build: the official r49 wasm emulator (SHA-256 checked after download) + `dist/`'s lower-case names + `manifest.json`; `web/build-site.mjs` folds it into `web/_site/x16/` |
| `x16/spike/web-title.png`, `x16/spike/web-level1.png` | the browser build's title screen and Level 1 (headless Edge, screenshot after `Enter`; `HELLO WORLD`, HUD `x5`/`x2`), proving the wasm build's HostFS, keyboard events and VERA output work |
| `x16/spike/irq-1-after-enter.png` | the first successful `Enter` into a level, after fixing "the KERNAL IRQ is sourced from VERA VSYNC" |
| `x16/spike/shot-soundtest.png` | pressing `T` on the title opens the SFX/BGM test screen (`SFX 00 BGM 1`, right switches to BGM mode) |
| `x16/spike/shot-mute-keys.png` | the two mute keys `M`, `N`: the title shows `MUSIC OFF` and `SOUND OFF` at the same time |
| `x16/spike/shot-cow-level.png` | title `1` (SELECT) + `Enter` → `COW LEVEL` (level 0) |
| `x16/spike/shot-level-skip.png` | the level-skip cheat `z,left,x,z,left,x` + `Enter` + `1` → `LEVEL CLEAR` |
| `x16/spike/wavstat.py` | wav header repair + per-segment RMS/peak analysis (the audio evidence captured with `-Wav`, §7.9) |
| `x16/spike/tritrace.py`, `bytrace.py` | decode `AE_DEBUG_XY` (x/y/pad) and `AE_DEBUG_FALL` (1 byte: `y`+`pad`) `User debug 1` beacons (§7.10) |
| `x16/tools/shot.ps1` | the automatic screenshot tool (enumerates x16emu's own PID, sets HWND_TOPMOST, avoids the console window) |
| `x16/tools/playtest.ps1` | the key-injection + screenshot automation script (real scan codes, `KeySequence`, `right+z` held together, hard error when it cannot steal the foreground, `-Wav` recording and `-TailSeconds` to keep the emulator alive after the last key) |

**Done**: title-screen rendering, Level 1 loading and rendering, asset loading (lower-case names),
`read()` address preservation, the X16 keyboard/pad input layer (including the KERNAL IRQ and VSYNC
cadence fixes, §8), exchanging while falling (§6), the mid-air exchange checking every frame
(§7.10), snapping the mid-air landing to a tile and "the mirrored spot needs floor in vertically
mirrored levels" (§7.11), the credits platform line (§7.8), the special keys T/M/N/ESC and the cow
level / level-skip cheat (§7.9), the browser build (official wasm emulator + GitHub Pages, §9), and
a round of in-level play driven by key automation.
**Not done**: long hands-on confirmation of the feel (death/level-change were only verified for
rendering), only LV01/LV03/LV24 actually played out of the 26 levels (the load path is the same for
the rest), moving `ftm_envelopes.s`'s ZP off `$9A-$9F` (BASIC's ZP on the X16; it runs now but is a
latent bug), and DOS/SD packaging for release.

---

## 14. Recommended order for whoever picks this up

1. Play Level 1 once by hand with the keyboard/pad (`Enter` = START, arrows to move, `Z`/`X` = A/B)
   and confirm the feel of `keyboard_pad()`'s X16 branch plus the death/level-change flow.
2. Move `ftm_envelopes.s`'s ZP off `$9A-$9F` into `$22-$7F` (the X16 build still runs, but
   `$9A-$9F` is BASIC's ZP area on the X16, so it is a latent bug).
3. (Done) `$0314/$0315` VSYNC frame counter: see §8; it can be used to measure whether the 60 Hz
   cadence and the music tick are stable.
4. Package (`.zip`/SD image): install `dist`'s assets plus `GAME`/`MUSIC`/`LOADER.PRG` into the X16's
   DOS file system and confirm it runs without HostFS.
5. Only then the optional items: change `io_cx16.c`'s VRAM staging to a banked RAM buffer, removing
   the risk of `$A000-$BFFF` and the staging address stepping on each other.

---

## 15. References

- This repo: `vera/AGENTS.md` (the Apple II VERA build and its status), `vera/src/a2vera/main.c`,
  `vera/build/build_a2vera.ps1`
- cc65: `C:\dev\cc65\lib\cx16.lib`, `cfg\cx16.cfg` (`STARTADDRESS $0801`, ZP `$22-$7F`,
  `__HIMEM__ $9F00`, `__STACKSIZE__ $0800`)
- X16 official documentation: `C:\dev\emu\x16emu` (`readme.txt`, `prg.txt`: VERA registers, KERNAL
  `LOAD/SETNAM/SETLFS`, `joystick_get`, `memory_copy/fill`)
- Reference ports: `C:\dev\time-pilot\TimePilot-CX16` ↔ `TimePilot-IIvera` (no shared HAL, a
  single-file `main.c` rewrite), `C:\dev\x16-hero-vera` (LLVM-MOS),
  `C:\dev\cx16-othello-vera`
- Community examples: <https://github.com/mwiedmann/cx16CodingInC> (X16 C examples and VERA usage)
