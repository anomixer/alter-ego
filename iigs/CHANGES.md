# Changes

Newest first.  One entry per day of work, so the list lines up with the git history: everything done
on a given day appears in that day's entry.  Below this port's own entries are the silky-gs engine
releases it came from.

## 2026-11-01 — Alter Ego for the Apple IIgs

The day's work is a single (squashed) commit: the port and its polish, the deliverables moved out of
the source tree, the archived `//e` tree, the repository rename and the two-target README.

### The port

- **Alter Ego now runs on the Apple IIgs** through silky-gs, a native 65816 NES runtime: the
  unmodified 32 KB NES program runs as a coroutine beside the GS task and its PPU/APU writes become
  Super Hi-Res graphics and DOC audio.  It is not an emulator, and no VERA card is involved.
- **Screen:** 320×200 SHR.  The 256×200 playfield is centred (`x_offset=16`) and maps NES scanlines
  16–215; the title, credits, GAME OVER and WELL DONE screens use their own full-screen treatment
  (`YOffsetAbs=31`).  Gameplay uses the engine's dirty-grid renderer, so only changed cells and
  sprites are redrawn each frame.
- **Audio:** the original FamiTone2 driver and song data, mixed by the engine at 60 Hz (60/120/240 Hz
  is selectable in the silky-gs panel) and played by the IIgs DOC.  Title theme, the five level
  themes, game-over and ending music, and the fifteen original effects.
- **Playable end to end:** title menu (START GAME, START LEVEL, MUSIC, SOUND), credits, levels 1–25
  with the A/B exchange move, pause with RESUME / RESTART / EXIT GAME, GAME OVER, WELL DONE and the
  ending.
- **2.8 MHz is enough:** at the factory speed a full gameplay render fits inside one VBL
  (`renderVblTicks` reads 1 every frame) and the sea keeps its 16-frame cadence, about 30 game
  frames/s.  Booting reaches the title in roughly 20 s at 16 MHz, or 2–3 minutes at 2.8 MHz.

### Graphics

- Restored the animated sea without the 12 fps full-screen CHR toggle: page-0 tiles `$E0–$E3` hold the
  alternate wave art, and only the water nametable cells are rewritten every 16 game frames.
- Fixed the garbled top-left HUD counters: the water art had overwritten tile `$E4`, the `×` glyph of
  the stats meta-sprite.  The four wave variants now live in `$E0–$E3`, so the player/ego counts read
  `×5` and `×2` again.
- Palette fixes for gameplay: blue-clothed player, green wall plants, blue/cyan water (the sea no
  longer shows a red line).
- Fixed stray sea stripes during the exchange move: the NES flash recoloured sprite-palette entries
  that alias onto the background's SHR slots.  The flash is now a visibility blink of the ego sprites
  — no palette writes and no palette-bit switching — so both egos keep their normal colours
  (white head, blue clothes) and the water is untouched.
- Credits screen: rows tightened to make room for two IIgs lines (`APPLE IIGS VERSION BY`,
  `ANOMIXER 2026`) and held for 6 s; START skips it.

### Input

- **X/Z no longer depend on Caps Lock.**  `_pad_poll` matches the low five bits, so both letter cases
  and the Ctrl-X/Ctrl-Z and raw ADB codes all work; repeated quick presses trigger every time.
- The title's sound test moved to **Tab** (NES Select), because a one-key-at-a-time keyboard cannot
  type the NES chords: Tab opens and closes it, Left/Right pick the SFX or BGM field, Up/Down change
  the value, **Space** (or X) auditions the selection, **Z** stops the music, and Return leaves the
  test and starts the game.  The selected pair is pale yellow, the other pair matches the menu text.
- The hidden **Cow Level** is reachable as START LEVEL `00` (range 0–25).  The default stays 1 and
  START GAME still forces level 1, so a normal boot never lands on it by accident.

### Audio

- **The music is silent only while the next level loads.**  LEVEL CLEAR keeps playing; from the
  switch into the next level (black load screen) through the READY blink the music is paused, and it
  restarts on the frame the ego becomes controllable.  The hold lives in `rom_exec.s`, so the NES
  program (`prg.bin`) is unchanged: the engine sets FamiTone2's pause bit while the screen is off and
  clears it 52 NES frames after the screen returns.
- The title, credits and game-over music use the same screen-off/screen-on path, so they come back
  about a second after their screen appears.  The pause bit is re-asserted every frame because the
  level's own `music_play` clears it.
- The pause bit is NES RAM `$0101` bit 7, written one byte wide.  A 16-bit write also touched `$0102`
  and froze the title screen; that bug was found and fixed before shipping.

### Files and build

- **Deliverables moved out of the source tree:** the boot image and the application are now
  `build/iigs/AlterEgo.2mg` and `build/iigs/AlterEgoGS`, next to the VERA port's images in
  `build/a2vera/`.  `build.js` publishes the assembled application there, and the GSplus configuration
  (`iigs/emu/gsplus-alterego.kegs`) points at the new image.  The stale 2026-10-29 image
  (`AlterEgoOld.2mg`) was deleted.
- The boot image was renamed `AlterEgoJml.2mg` → **`AlterEgo.2mg`** and the configuration to
  `gsplus-alterego.kegs`; the `Jml` suffix was a leftover label from the earlier silky-gs tree and
  nothing inside the image depended on it (volume `/ALTEREGO`, program `/ALTEREGO/AlterEgoGS.S16`).
- `prg.bin` must stay exactly 32,768 bytes; it is reproduced byte for byte from the objects imported
  into `iigs/prg-src/` with cc65 + `ld65`, so a PRG change is rebuilt there and relinked before the
  Merlin build.
- The shipped artefacts are `build/iigs/AlterEgo.2mg` (10,485,824 bytes, SHA256 `93A3004F…`),
  `build/iigs/AlterEgoGS` (313,359 bytes, SHA256 `88281425…`) and `iigs/src/games/alterego/prg.bin`
  (32,768 bytes, SHA256 `C4CB0445…`).

### Repository

- Archived the retired Apple `//e` working tree under `docs/archive/apple2e/` and imported the parts
  that existed nowhere else: `iigs/prg-src/`, the port evaluation docs and the DHGR preview.
- Renamed the repository `alter-ego-vera` → **`alter-ego`**, since it now hosts two Apple II targets;
  documented paths, the GSplus configuration and the GitHub URL were rewritten, and the VERA release
  images keep their `alter-ego-vera*` filenames.
- `README.md` now leads with a two-target table, has an **Apple IIgs port (silky-gs)** section (screen,
  audio, speed, `prg.bin` rule, GSplus launch, controls, screenshots), a `### Verification` subsection
  per port, and a `## Documentation` index of the design records.

### Tooling

- **`npm run test`** boots the committed image in GSplus, checks that the title screen drew, presses
  Return and checks that Level 1 came up.  The checks are pixel checks on GSplus' own F10 screenshots
  (grey playfield frame, orange logo, teal water), so a rendering regression fails the run instead of
  only being noticed by eye.  Captures stay in `iigs/tmp/test/`, so no tracked file is touched.
  `--keep`, `--boot-timeout <s>`, `--level-timeout <s>` and `AE_GS_GSPLUS` are available.
- `npm run test:unit` keeps the engine's vitest suite, and `npm run build:alterego` rebuilds the
  application (Merlin32 + Cadius) from `src/games/alterego/`.

### Play-through

- A play-through from boot to the ending on the shipped image ran normally (the player's report, not
  an automated check), so levels 1–5, LEVEL CLEAR and the WELL DONE ending are exercised in practice.
  No captures were taken during that pass: GAME OVER, WELL DONE, LEVEL CLEAR and levels 2–5 still have
  no screenshot in the repository, and that is now a documentation gap rather than an open defect.

## 2026-10-21 — silky-gs engine release

### Input

- **Joystick support in every game.**  Choose JOYSTICK as the input TYPE on the INPUT menu.  The stick
  is read while the game runs without slowing it down: full renders time it with probes built into the
  scanline renderer, and dirty renders with scanline interrupts that are only on while they run.
  Joystick buttons 0 and 1 are the A and B buttons, and the keyboard keeps working alongside.
  - CALIBRATE (center the stick, then press a key), SENSITIVITY (1 - 7) and TEST (shows the direction
    each axis reads) on the INPUT menu.
  - OFFSET (0 - 7) for emulators that run the renderer faster than a real IIgs (e.g. GSPlus); leave it
    at 0 on real hardware.
- **New DRIVERS menu: BASIC or J13 keyboard driver.**
  - BASIC reads one key at a time, the last key pressed.  Its key maps now ignore Shift, Control and
    Caps Lock, so a direction key keeps working while a modifier is held as a button.  Pressing a new
    direction replaces the old one, and nothing can get stuck once the keys are released.
  - J13 (adapted from the IIgs Wolfenstein 3D port) tracks up to three held keys, so diagonals work, by
    reading the keyboard microcontroller on ROM 00 / 01 machines.  On ROM 3 and most emulators it
    works like BASIC.
- **Player 2's default keys are now W A S D** (they were I J K L, which clash with the arrow keys when
  Control, player 2's A button, is held).

### Built-in keys

- **No Control key needed any more.**  The built-in keys are now:

  | Key | Action |
  |---|---|
  | `?` | Configuration screen |
  | `!` | Redraw the whole screen |
  | `@` | Show / hide the sprites |
  | `#` | Show / hide the background |
  | `R` | Reset the game (like the NES console's RESET button) |
  | `Q` | Quit, after a confirmation screen (Y quits, N or Escape goes back) |

- A key set as a controller key now works as the controller, not as a built-in key (`?` always opens
  the configuration screen).

### Speed

- Faster dirty rendering: more of the grid work is deferred, the grid encoding dispatches straight to
  its routines, and the erase passes no longer switch data banks.
- Faster sprites: palette selection is deferred for non-compiled sprites, the OAM scan is quicker,
  and the 8x16 sprite path is streamlined.
- All 512 background tiles compile into a single bank.

### Disks

- **README.TXT** at the top level of every disk: the keys and settings that every game shares.
- `npm run build:dist` builds one 800KB disk per game.
- New icons.

### Internal

- The engine moved into its own ENGINE segment, shared by every game, with each game's constants in
  `Config.s` and its callbacks in `Hooks.s`.  This made room in the MAIN segment for every game.

## 2026-10-13 — silky-gs engine release

- Moved all games to the new palette build tool developed for Zelda.
  - Many palette transition issues fixed in Super Mario Bros, Mario Bros, Ice Climber and Excitebike.
- Smaller on-disk file sizes for all games (custom OMF packer).
- All games moved into separate folders on the disk image, which keeps the preference files from
  cluttering the top level.
- New default palette provided by @fatdog.
- Optimized Super Mario Bros ROM code to slightly improve the frame rate.
- Sprites can be drawn at single-pixel positions (most games; Super Mario Bros keeps 2-pixel steps).
- Fixed input handling in Wumpus.
- Restored the FAST BLIT mode (selectable in the configuration).  This mode renders only the even
  scanlines and makes scrolling games somewhat playable at stock speed.
- Lots of configuration UI changes.
  - Games can now define their own settings.
  - Configuration enabled in all games.
  - Preference files are expandable and should have a stable file format going forward.
