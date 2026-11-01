# AGENTS.md — alter-ego Apple //e port (ARCHIVED 2026-10-26)

> **ARCHIVED.** //e DHGR is no longer the mainline: its fixed palette and
> color-cell/fringing limitations make NES art a demake. Current target is
> **Apple IIgs / silky-gs**, evaluated in
> [docs/PORT-IIGS-SILKY-EVAL.md](docs/PORT-IIGS-SILKY-EVAL.md). The //e material
> below is retained as historical/game-logic reference; do not resume the //e
> decode investigation unless explicitly reopened.

Historical status snapshot (//e), kept for reference. The next session should
start from the IIgs evaluation, not from the //e steps below.

## Historical //e goal (archived)

Port the cc65 NES homebrew **alter-ego** to the Apple //e (128K), built with
cc65 (`C:\dev\cc65`) or llvm-mos. Deliverable is a bootable DOS 3.3 disk image
at `build\a2\ae2_game.dsk`.

- **Graphics: DHGR everywhere (real 16-colour palette), game logic 60Hz,
  rendering 30fps** (user confirmed 2026-10-08; the HGR mono-artifact route
  produced garbled/unreadable screens).
- **Music**: Mockingboard (AY-3-8913) via FamiTone2.
- Levels load on demand, one at a time, on clear — not all in memory.

## DHGR migration status (2026-10-08)

`src/a2/dhgr.s` **rewritten** to the verified geometry (pom2games dhgr.c:19-25):
560x192, 7px/byte, 80 slots/line = 40 main + 40 aux, addr = hgr_row(y)+(slot>>1),
slot even -> aux / odd -> main, RAMWRTON/OFF around aux stores, **80STORE OFF**
(not SET80COL). API: `dhgr_init` (pom2games dhgr_asm.s:134-141 sequence),
`dhgr_clear` (fills both banks), `dhgr_draw_screen` (decodes an interleaved
80-slot page RLE). Assembles clean (`ca65 --cpu 6502`). `dhgr_set_row`/`put8`
removed for now (gameplay tile placement is a later phase).

`tools/a2_art.py` now also emits **DHGR art** (`dhgr_page()` + `chr_tiles`):
`build/art/titledh.bin` etc., interleaved 80-slot page RLE. Title palette:
ALTER EGO (tiles 0x01-0x2e+0xb8-0xbf) -> ORANGE(9)/BROWN(8); PRESS START
(tiles 0x40-0x7f) -> BLUE(6)/DARKBLUE(2). Verified: `build/a2/dhgr_title_render.png`
shows ORANGE ALTER EGO + BLUE PRESS START. All DHGR payloads fit the $1000
staging page (largest WELLDONE 4021 B).

**DHGR engine VERIFIED WORKING (2026-10-09).** AppleWin headless automation:
`C:\dev\applewin\x64\Release\AppleWin-x64.exe -d1 <dsk> -model apple2e
-run-cycles N -screenshot-and-exit out.png -no-full-screen` (note: `-run-cycles`
auto-exit does NOT reliably fire / produce a PNG in the Release build; the user
verifies via AppleWin window manually). Test disk `build/a2/dhgr_solid.dsk`
(init + fill ORANGE): rendered SOLID ORANGE correctly after fixing the `ptab`
in `src/a2/dhgr.s` (the hardcoded colour-phase table was wrong — ORANGE showed
as GREEN). So `dhgr_init` (80STORE OFF + COL80ON + HIRES + MIXCLR + DHIRES_ON +
TXTCLR + LOWSCR), `dhgr_clear` (both banks), `fill_bank2`, `ptab`, and the
RAMWRTON/RAMWRTOFF bank switching ALL WORK.

**ROOT CAUSE FOUND + FIXED (2026-10-10) — the dhgrtitle demo was MISLINKED.**
`build/a2/dhgrtitle.cfg` had MAIN starting at $0803 while the BIN header
claims $6000, so BRUN's entry executed `jsr $0813` into the Applesoft/HELLO
region — the machine went sideways and landed in the Monitor ("]" +
"4440- A=C8 …"). `dhgr_draw_screen` itself was never actually exercised in
the emulator. Fixed: MAIN/STARTADDRESS now $6000 (size $3600); map shows
LOWCODE $6000, `_dhgr_init` $6010, `_dhgr_clear` $6028, `_dhgr_draw_screen`
$60DE; the bin's jsr targets are all $60xx. Verified `a2_dsk_verify.py`
RESULT: OK (load $6000 len 748 exact). Earlier "renders ONLY ORANGE"
observation came from the same mislink — re-judge the draw after the fix.

Second gate: AppleWin's aux card must stay CT_Extended80Col or VF_DHIRES is
cleared (Video.cpp:225-239) and the screen decodes as plain HGR (rainbow
stripes = plain-HGR artifact RGB, per `tools/err_hue.py`). Boot with
`-aux ext80`. Verify screenshots show lores-palette RGB
(242,94,0 / 85,85,0 / 13,161,255 …), not plain-HGR artifact RGB.

**MODEL GATE FOUND (2026-10-11) — `-model` picks WHICH //e.**
`-model apple2e` = A2TYPE_APPLE2E = **original** //e; `-model apple2ee` =
A2TYPE_APPLE2EENHANCED = **enhanced** //e (CmdLine.cpp:690-693). The
`IS_APPLE2` macro (Common.h:183: `(g_Apple2Type & (APPLE2E_MASK|APPLE2C_MASK)) == 0`)
is TRUE on the ORIGINAL //e, so the 0x0D/0x5E/0x5F soft-switch cases
(Video.cpp:191-208) are gated `if (!IS_APPLE2)` and NEVER apply on
`-model apple2e` — VF_80COL/VF_DHIRES could never latch there. All boots
must use **`-model apple2ee -aux ext80`**. Window title proves the model:
"Apple //e (original) …" vs "Apple //e (enhanced) …".

**RE-BOOTED ON apple2ee (2026-10-11)**: `run_dhgrtitle_ee.ps1` →
`build/a2/shots/awee_1.png … awee_8.png`, window "Apple //e (enhanced)
Emulator - Color (RGB Card/Monitor)". The screen is now MOSTLY DHGR: the
glyphs are visible as SOLID ORANGE (ALTER EGO row) and SOLID BLUE (PRESS
START row) blocks with the remaining background stripes in artifact RGB.
hue1.py still counts ~50% hgr-artifact colors because the BACKGROUND is
being decoded by a different path than the glyph rows — see OPEN BUG below.

**OPEN BUG (enhanced //e): glyph rows are DHGR-solid, background is not.**
The awee captures show orange/blue glyph areas + rainbow-striped background.
Hypotheses: (a) `dhgr_clear` fills BOTH banks with the same orange byte —
then `dhgr_draw_screen` only repaints the glyph rows, leaving clear-fill
bytes that decode plain-HGR (check: what colour is `dhgr_clear`'s fill?
ORANGE vs BLACK); (b) VF_MIXED/80COL boundary per scanline (NTSC.cpp
mixed-scanline logic); (c) aux/main interleaving wrong for part of the
page. Compare `dhgr_solid.dsk` (clear-only, whole-screen ORANGE verified on
apple2e) on apple2ee: if solid orange there too, dhgr_clear is fine and the
issue is in draw_screen's byte pattern vs clear's fill.

**DIAGNOSIS PROGRESS 2026-10-11 (paused by user; record exactly where this
stands, do NOT redo these measurements):**

1. **Hypotheses (a)/(c) are DISPROVEN — the mislink was the real blocker.**
   `boot_solid_ee.ps1` ran dhgr_solid.dsk on apple2ee → `awsolEE_1.png`; window
   title "(enhanced)". `solidhue.py`: awsol_1 vs awsolEE_1 inner regions are
   PIXEL-IDENTICAL (diff 0 of 183,717), both solid (249,86,29) + black border.
   So model apple2e→apple2ee does NOT change the solid decode, and
   dhgr_clear/fill/ptab/bank-writing behave identically under both models.
2. **`dhgr_draw_screen` NOW WORKS (the 2026-10-11 mislink fix took).** Re-booted
   dhgr_title.dsk on apple2ee (`run_dhgrtitle_ee.ps1` → awee_1..8, all 8 hashes
   identical C5F081F8AAAC): the screen shows TWO glyph blocks (blue "PRESS
   START"-shaped block, orange "ALTER EGO"-shaped block) at the SAME positions
   as the offline reference render `dhgr_title_render.png`. The old
   "renders ONLY ORANGE" is GONE — the draw now paints both words. Re-judge:
   draw is working; do NOT re-chase the 2026-10-08 "solid orange only" lead.
3. **But the COLOURS are plain-HGR artifact RGB, not DHGR lores RGB.**
   `region.py` / `bluepix.py` on awee_1 (crop x55..110 y130..175 = blue block):
   (0,0,0) 32.7% + (147,11,124) violet 30.9% + (31,53,211) artifact-blue
   7.3% + green (67,200,0)/(0,118,12) 7.3% each. Orange block: (249,86,29)
   artifact-orange + (98,76,0) brown dominate. NO DHGR lores colours
   (242,94,0)/(85,85,0)/(13,161,255) appear anywhere in the captures.
4. **DECISIVE: simdecode.py / err_hue.py —** in the DHGR lores palette set,
   AppleWin's dhgr_title_run.png contains ONLY (0,0,0) x22872 + (255,255,255)
   x768, while the known-good software simulation `aw_decode_sim3.png`
   (tools/_aw_model.py, which replicates UpdateDHiResCellRGB's decode from
   titledh.bin) contains (0,0,0) x24548 + lores ORANGE (242,94,0) x1160 +
   BROWN (85,85,0) x950 + BLUE (13,161,255) x190 + DARKBLUE (42,42,165) x32.
   The glyph bytes are correct and the decode model is correct — AppleWin is
   simply not running the RGB-DHGR colour path on this boot.
5. **decode_view.py row RLE on awee_1 (y=150):** 4-px artifact stripe runs
   everywhere (147,11,124)→(0,0,0)→(67,200,0)… — that is the plain-HGR
   artifact scanline look, not 14-px lores colour cells. band.py per-column
   family: some columns read d=310 (full DHGR) but most are H-major.
6. **AppleWin source facts established (read directly, not from memory):**
   - `g_eVideoType` comes from registry "Video Emulation" =
     HKCU\...\Configuration → **2 = VT_COLOR_VIDEOCARD_RGB** (Video.h:22 enum
     order 0=mono,1=idealized,2=RGB,3=NTSC). So the machine IS on the RGB card
     path — not plain NTSC.
   - `RGB_SetVideocard` is called at AppleWin.cpp:767 with `g_cmdLine.rgbCard`
     (default RGB_Videocard_e::Apple). RGB card type default = "Apple" =
     **Video7_SL7 alias? NO** — CmdLine.cpp:711-718: "apple" is an alias for
     **Video7_SL7**? re-read: line 712 `g_cmdLine.rgbCard = RGB_Videocard_e::Apple;`
     line 714 SL7, 716 EVE, 718 Feline. `g_RGBVideocard` default is `Apple`
     (RGBMonitor.cpp:13). RGBMonitor.cpp:749-958 UpdateDHiResCellRGB maps
     nibbles: `color=((bits&7)<<1)|((bits&8)>>3); g_pPaletteRGB[12+color]` —
     "DHGR colors are rotated 1 bit to the right" (RGBMonitor.cpp:775). Our
     art encodes `color_bits(c)=((c>>1)|(c<<3))&15` (a2_assets.py:86-88) —
     these are the SAME rotation (inverse mapping), so the art encodes the
     CORRECT nibbles for AppleWin's palette index. The decode model in
     tools/_aw_model.py uses exactly AppleWin's formula and produces lores
     RGB — so IF AppleWin ran this path it would match the simulation.
   - **Registry "Video Emulation"=2 is decisive**: VideoSwitchVideocardPalette
     (RGBMonitor.cpp:1202-1209) → g_pPaletteRGB=PaletteRGB_NTSC for videocard
     Apple. VideoInitializeOriginal (1186-1197) overwrites entries [12..28)
     with NTSC-generated base colours and aliases HGR_BLUE→BLUE etc.
   - **The mystery**: with g_eVideoType=VT_COLOR_VIDEOCARD_RGB and mode
     HIRES+DHIRES+80COL, NTSC_SetVideoMode (NTSC.cpp:2157-2229) MUST pick
     updateScreenDoubleHires80RGB → UpdateDHiResCellRGB → lores colours. Yet
     the capture shows plain-HGR artifact colours instead. The 4-px stripe
     look of the background + glyph blocks matches UpdateHiResRGBCell /
     updateScreenSingleHires40RGB (NTSC.cpp:1578-1604) — i.e. the mode
     latched is HIRES-only (no DHIRES) or the 80COL flag is off. NEXT CHECK:
     what does `dhgr_init`'s store order actually latch? `sta $C05E` (DHIRES
     ON) then `bit TXTCLR ($C050)` — verify no later store to $C05F clears
     it, and that COL80ON ($C00D) precedes any $C05F. (Our init: $C000,
     $C00D, $C054, $C057, $C052, $C05E, $C050 — 80COL is set BEFORE DHIRES;
     RGB_SetVideoMode (RGBMonitor.cpp:1223-1249) latches g_rgbMode only on a
     0x5E→0x5F strobe pair, which we never send, so g_rgbMode stays 0 =
     RGB_Is140Mode() true = UpdateDHiResCellRGB colour branch — fine.)
   - Suspicion moves to: is NTSC_SetVideoMode selecting
     updateScreenSingleHires40RGB (HIRES && !DHIRES) instead? That would give
     exactly the artifact look (UpdateHiResRGBCell = 101/010 → colour, else
     B&W, = plain-HGR artifact on RGB). If VF_DHIRES is somehow NOT latched,
     the glyph bytes with bit7=1 decode as artifact orange/blue — matching
     what we SEE. Check by pressing F2/F3 in AppleWin (video mode display in
     title bar?) or via the debugger 'VM' command, or reading g_uVideoMode
     via debugger.
7. **Scripts state:** `build/a2/run_dhgrtitle_ee.ps1` (8-shot loop), `.ps1`
   run via `iex (Get-Content -Raw ...)`; AppleWin is NOT running right now;
   registry Slot 7 "Last Harddisk Image 2" now EMPTY (cleared; jukebox.hdv
   still exists so no dialog appears anyway). simdecode/err_hue outputs are
   already recorded above — DO NOT re-run them for identical results.

Gotcha (automation): AppleWin persists "Last Harddisk Image N" registry
values (HKCU\...\Configuration\Slot 7); a stale deleted-path value pops
"Unable to open the file" dialogs that freeze screenshots. Clear it with
`Set-ItemProperty 'HKCU:\Software\AppleWin\CurrentVersion\Configuration\Slot
7' -Name 'Last Harddisk Image N' -Value ''` before automation boots.

**NEXT STEP (resume here):** prove which renderer function AppleWin used.
Options: (A) AppleWin debugger F7 + `VM`/`v` command to dump the video-mode
flags while dhgrtitle is displayed; (B) log/trace `VideoSetMode` writes by
watching $C05E via the debugger watchpoint (0x5E/0x5F writes); (C) boot with
`-video-mode=composite-monitor` (VT_COLOR_MONITOR_NTSC) to see whether the
plain-NTSC path shows lores-coloured glyphs (if YES → the RGB path is being
skipped; if NO → VF_DHIRES never latched); (D) instrument the capture: compare
an intentional 0x5F write (DHIRES OFF test disk) — if the screen becomes
EVEN MORE artifact-y, DHIRES was already off. Whichever settles it, then
either (i) fix the latch order in dhgr_init, or (ii) if DHIRES is latched but
the RGB double-hires path still outputs artifacts, re-read NTSC.cpp:2157-2229
mode selection with a debug breakpoint.

**Remaining after the decode issue:** wire neslib.c to dhgr_*, rewrite spr.s
for DHGR sprites, 30fps render loop, DHGR level rendering, repackage. **DHGR
can only be verified on AppleWin** (a2run/a2_emu are II+ 48K, no aux RAM).

## Toolchain / build

```
cc65 -Oi/-Os            -> ca65 -t apple2enh --cpu 6502 -> ld65 -C src/a2/a2_128.cfg
```

**MANDATORY:** `--cpu 6502` on every ca65/cc65 call. The default 65c02 target
emits `bra` as `$80` (= `STY ($00,X)`) and `inc a` is 65c02-only.

Build script: `tools\build_a2.ps1` (run via `iex (Get-Content -Raw ...)` because
script execution is disabled). It generates assets, assembles music/cold/levels,
packs the DOS 3.3 disk, and verifies every file against the packed image.

Rebuild output: `RESULT: OK` at the end.

## Memory layout (src/a2/a2_128.cfg)

```
$0050-$00AF  program zero page      $00B0-$00FF  cold image zero page
$0400-$07FF  text page (DOS)        $0800-$0FFF  VRAM shadow
$1000-$17FF  streaming staging page $1800-$19FF  DOS page-zero swap
$2000-$3FFF  HGR page 1 (game view) $4000-$4FFF  TILES   (BLOAD'd)
$5000-$5FFF  MUSIC (BLOAD'd)        $6000-$95FF  program+BSS+stack
$9600-$BFFF  DOS 3.3                $D000-$DFFF  COLD: ftm.s+sys.s (RAM bank)
```

Everything that can live on disk is BLOAD'd: tileset, music, 26 levels, four
art screens. Disk: 12,261 program + 4,096 tiles + 3,986 music + 1,198 cold +
10,398 levels + 1,317 art.

## Disk layout (build\a2\ae2_game.dsk)

Boots DOS 3.3, auto-runs HELLO, which BLOADs COLD->$2000, TILES->$4000,
MUSIC->$5000, TITLEH->$1000, CREDITSH->$1900, then BRUN AE2GAME.

Files: AE2GAME, COLD, TILES, MUSIC, LV00..LV25, TITLEH, CREDITSH, GAMEOVERH,
WELLDONEH.

## Launching AppleWin

```
Start-Process 'C:\dev\applewin\AppleWin-x64.exe' -ArgumentList '-d1','C:\dev\alter-ego\build\a2\ae2_game.dsk','-model','apple2ee','-no-full-screen','-aux','ext80'
```

**Kill AppleWin before rebuilding** (it locks the .dsk). The AppleWin screenshot
is the ground truth for graphics.

## Emulator observation channel

`tools\a2_emu.py` is the only working observation channel (host debugger accepts
no input, CopyFromScreen fails, no sound device).

- Budget `--max-steps` = frames x 110,000. `--fast-tick` cuts per-frame delay.
- `--stop-at 0x65BB` captures the title (title paint `jsr $6181` at `$65B8`,
  return `$65BB`). `main()` paints credits ($1900) THEN title ($1000).
- `--dump-hgr FILE` writes 40 bytes/scanline in DISPLAY order to a text file.
- `--hgr-guard` only accepts real store PCs.
- `--probe ADDR` reads CPU state BEFORE instruction; probe ONE address alone.
- Inject keys `--key-at <pad_trigger> --key-once 1`.
- Confirm global addresses by disassembly via `tools/a2_dis.py`.
- Run with `*> file` redirect; `subprocess.run(capture_output=True)` hits EPERM.

## HGR technical rules

- **HGR bit 7 is the display SYNC bit** — every byte written to the page must
  have bit 7 SET. HGR black = `$80`, white = `$FF`; `$00` = stripe pattern.
  `hgr_clear` fills `$80`; `hgr_put8`/`put_byte` do `ora #$80` before store.
- **HGR scanline layout**:
  `addr[y] = 0x2000 + (y%8)*$0400 + ((y/8)%8)*$80 + (y/64)*$28`; 192 pairs
  in `$2000-$3FD0`.
- **HGR bit order (AppleWin): bit 6 = leftmost pixel, bit 0 = rightmost.** A
  bit-0-leftmost byte renders MIRRORED on AppleWin.
- **HGR colour = NTSC artifact, parity-locked.** The rule (kit's own emulator
  `a2run.c:374-418`): `pal[hi][x&1]` — bit7=1 → blue (even col) / orange (odd
  col); bit7=0 → violet (even col) / green (odd col). A pixel with a lit
  neighbour reads WHITE; an isolated dot takes its column colour and is drawn
  2 px wide. To force a chosen hue, keep only the pixel parity that reads as it
  and OR in bit7 (see `colorize_byte()` in `tools/a2_art.py`): ORANGE =
  `0x80|(mono&carrier)` with carrier `0x2A` on even cols / `0x55` on odd cols;
  BLUE swaps the carrier.

## CHR blob (src/tileset.chr)

**STANDARD NES CHR**: bit 0 = leftmost pixel (verified). `chr_tiles()` uses
`rows[p] = pixel p` via bit `(7-p)` (the blob is stored bit-reversed).

## RESOLVED — title colors (ALTER EGO orange, PRESS START blue)

**Symptom (fixed):** AppleWin title "ALTER EGO / PRESS START" read correctly
in shape but the colors were wrong (blue/violet instead of orange/blue).
The NES reference (`C:\dev\Alter_Ego.nes`) shows:
- "ALTER EGO" = **ORANGE**
- "PRESS START" = **BLUE**

### Root causes (both fixed this span)

1. **Both HGR renderers used a WRONG NTSC-artifact rule.** The old rule in
   `tools/a2_emu.py render_hgr` and `tools/a2_offline_render.py` inverted the
   bit7 family (bit7=1 → violet/blue) and omitted the "two adjacent dots are
   white" rule. The real artifact (from the kit's own emulator,
   `pom2games/dev/tools/a2run/a2run.c:374-418`):
   `pal[hi][x&1]:  hi=0 -> violet(even)/green(odd);  hi=1 -> blue(even)/orange(odd)`;
   a pixel with a lit neighbour (x-1 or x+1) reads WHITE; an isolated dot takes
   its column colour and is drawn 2 px wide. Both renderers now copy that
   algorithm verbatim.

2. **The title art was mono (bit7 mostly 0), so it read as the green/violet
   family, never orange/blue.** `tools/a2_art.py hgr_page()` now colorizes the
   title glyph tiles: `colorize_byte()` keeps only the pixel parity that reads
   as the chosen hue and ORs in bit7. ORANGE needs hi=1 + odd absolute column,
   BLUE hi=1 + even absolute column; since absolute col x = col*7+k (7 odd),
   the carrier is `0x2A`/`0x55` selected by `col&1`. The two words are disjoint
   tile sets: "ALTER EGO" = tiles 0x01-0x2e + 0xb8-0xbf, "PRESS START" =
   tiles 0x40-0x7f (`TITLE_PRESS_START_TILES`). Colorize is applied to the
   TITLE screen only (credits/gameover/welldone stay mono).

Verified by `tools/a2_offline_render.py` → `build/a2/off_bit0.png`: "ALTER EGO"
now reads ORANGE, "PRESS START" BLUE — matching the NES reference. `titleh.bin`
RLE = 3,074 B (fits the $1000 staging page).

### Next step (unchanged, still open)

Confirm the full emulator run (`tools/a2_emu.py`) paints the title correctly
end to end (the offline render only exercises the art; the game paints via
`hgr_draw_screen((void*)0x1000)` in `src/a2/neslib.c:481`). If the emulator
still shows wrong colours after this, re-check `hgr_draw_screen`'s consumption
of the colorized bytes (bit7=1 is now expected throughout the title).

### What was established this span

1. **Bit order is CORRECT now** (bit-0-leftmost art + bit-0-leftmost render).
   The title is NOT mirrored anymore; it reads "ALTER EGO / PRESS START".
2. **The shadow is INTENDED** — the CHR glyph (tile 1) uses color 3 (main) +
   color 2 (shadow/outline). The user said "revert it" after I tried removing
   the shadow, so color 2 is back in `tile_to_hgr` (`if rows[r*8+k]:`).
3. **The emulator render_hgr was SIMPLIFIED** (bit7->violet/green). I fixed it
   to the real HGR artifact:
   - bit7=0 -> green (even pixel) / orange (odd pixel)
   - bit7=1 -> violet (even pixel) / blue (odd pixel)
4. **CHR tile 1 colors** (from `tools/a2_chrcolors.py`): color 3 = main body,
   color 2 = outline/shadow, color 1 = bottom underline.
5. **NES ROM parsed** (`tools/a2_nes.py`, mapper 0, PRG 32768, CHR 8192).
   Candidate palette at PRG+0x404E:
   - palette 0: `[16, 1a, 21, 1d, 16, 1a, 21, 1d, 16, 1a, 21, 1d]`
   - palette 1: `[16, 1a, 21, 1d, 18, 1c, 23, 1f, 18, 1c, 23, 1f]`
   - palette 2: `[18, 1c, 23, 1f, 18, 1c, 23, 1f, 16, 1a, 21, 1d]`
   - palette 3: `[16, 1a, 21, 1d, 16, 1a, 21, 1d, 16, 1a, 21, 1d]`

### Key files

- `tools\a2_assets.py` — `chr_tiles()` (rows[p]=pixel p), `tile_to_hgr()`
  (bit-0-leftmost, includes color 2), `main()` regenerates `build/hgr_tiles.bin`.
- `tools\a2_emu.py` — `render_hgr()` (~line 977): now uses real HGR artifact
  (bit7 + pixel parity); `seed()` loads art.
- `tools\a2_art.py` — `hgr_page()` (~line 102): tile placement
  `page[(out_row*8+r)*40 + col] = b[r]`.
- `tools\a2_chrcolors.py` — dumps CHR tile colors.
- `tools\a2_nes.py` — parses the NES ROM for the palette.

### Next step

Determine the correct bit7 values so the title shows ORANGE (top) + BLUE
(bottom). Likely: map CHR color 3 (main) -> ORANGE (bit7=0) for "ALTER EGO" and
BLUE (bit7=1) for "PRESS START", OR the title uses the palette block at
PRG+0x404E (palette 0 = `16/1a/21/1d` which are likely black/dark/light grays;
palette 1 = `18/1c/23/1f`). The NES title art uses two palettes for the two
words. Verify against the NES ROM CHR + palette, then set the correct bit7 in
`tile_to_hgr` (or add a palette-mapping step in `a2_assets.py`).

## Verification scripts

- `tools\a2_cmp4.py` — compares emulator `--dump-hgr` output to `titleh.bin`
  (masks bit 7).
- `tools\a2_offline_render.py` — renders `build/art/titleh.bin` RLE in display
  order: `off_bit0.png` (pixel k = bit k), `off_bit6.png` (pixel k = bit 6-k).
- `tools\a2_chrbig.py` — renders CHR tile 1 at 16x scale.
- `tools\a2_chrcolors.py` — dumps CHR tile color indices.
- `tools\a2_px.py` — compares two render PNGs pixel-by-pixel (glyph shape).
- `tools\a2_tilecheck.py`, `tools\a2_combo.py` — tile byte checks (combo.py is
  broken: uses `art.nametable()` which doesn't exist).

## Hard rules

1. `--max-steps` budget = frames x 110,000.
2. Re-read `.map` after every rebuild.
3. Disassemble only via `tools/a2_dis.py`.
4. `--hgr-guard` only real store PC.
5. Probe ONE address alone.
6. Inject keys `--key-at <pad_trigger> --key-once 1`.
7. Confirm global addresses by disassembly.
8. Kill AppleWin before rebuilding (locks .dsk).
9. Python: `C:\Users\USER\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`.
10. PowerShell 5.1 FullLanguage; `iex (Get-Content -Raw file)`; each `pwsh`
    call fresh; `$` in inline python is mangled — write `.py`.

## Environment notes

- AppleWin 1.32.1.0 at `C:\dev\applewin\AppleWin-x64.exe`.
- GPL-3.0 exposure: kit sources (`a2run`, `dos33.py`, `crt0_apple2.s`,
  `dos.asm`) used as internal tooling/reference; `crt0_dos33.s`, `dosload.s`,
  `neslib.c`, `lvload.s`, `ftm.s`, `sys.s`, `pushax_fix.s` written from
  documented protocols.

## Historical //e "Do NOT" (archived)

These rules applied while //e DHGR was the mainline. They are historical and no
longer define the project goal; the //e route is archived. The current IIgs
work starts from [docs/PORT-IIGS-SILKY-EVAL.md](docs/PORT-IIGS-SILKY-EVAL.md).

At archive time the title color bug was still OPEN and the game did not run
end-to-end on //e.
