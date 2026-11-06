# Changes

Newest first.  One entry per day of work, so the list lines up with the git history: everything done
on a given day appears in that day's entry.  Below this port's own entries are the silky-gs engine
releases it came from.

## 2026-11-06 — the first release is `v0.0.2`, and it carries the X16 SD-card package

Both from a direct request: 「release 的第一個 release 要加 alter-ego-x16-sd.zip, 幫改 (tag也要改
v0.0.2)」.  The single GitHub release is no longer IIgs-specific, so its tag is renamed and a third
asset joins it.

- **Tag renamed** `iigs-v0.0.2` → **`v0.0.2`**, now pointing at the 2026-11-06 commit, so the
  release's source archive carries every port (the IIgs assets below are unchanged bytes, and still
  byte for byte the files `iigs/build/` holds).  The old tag name is gone from GitHub; the history in
  this file and in `AGENTS.md` keeps it as the label of what was released on 2026-11-04.
- **New asset:** `alter-ego-x16-sd.zip` — 41,042 bytes, SHA256
  `BB00F8868F14E1ACF4F0B8E9A381F076FEE779E05BC798FF2144D6DA35B1F8FC` — the Commander X16 SD-card
  package, the same bytes as the tracked `x16/build/alter-ego-x16-sd.zip` (37 entries: `LOADER.PRG`,
  `GAME`, `MUSIC`, the asset files, `LV00`–`LV25` and `README.TXT`).  It is reproducible:
  `x16/tools/pack-sd.ps1` repacks the same `x16/spike/dist/` to the same hash.

| Asset | Bytes | SHA256 | What it is |
|---|---|---|---|
| `AlterEgo.2mg` | 819,264 | `4115CB7F…` | 800 KiB GS/OS boot disk, unchanged |
| `AlterEgo-full.2mg` | 3,670,080 | `3D7EA71E…` | full System 6 volume, unchanged |
| `alter-ego-x16-sd.zip` | 41,042 | `BB00F886…` | Commander X16 SD-card package (see `x16/README.md`) |

Docs updated where the tag was named: `README.md` (the IIgs download bullet and the PLAY HERE row),
`iigs/README.md` (status and the release section), and `x16/README.md` / `x16/readme-tw.md` now say
the package ships as this release's asset.

## 2026-11-04e — released: tag `iigs-v0.0.2`

The port is published: tag **`iigs-v0.0.2`**,
<https://github.com/anomixer/alter-ego/releases/tag/iigs-v0.0.2>, with the two disks below as release
assets.  Both are the tracked files in `build/`, byte for byte — nothing was repacked for the release.

| Asset | Bytes | SHA256 | What it is |
|---|---|---|---|
| `AlterEgo.2mg` | 819,264 | `4115CB7F…` | the 800 KiB GS/OS boot disk, game as `/SYSTEM/START`, no Finder; Q → Y ends the game on the exit screen |
| `AlterEgo-full.2mg` | 3,670,080 | `3D7EA71E…` | the full System 6 volume, `/ALTEREGO/AlterEgoGS.S16`, Finder desktop; Q → Y returns to the Finder |

Before publishing, both disks were opened with Cadius and their programs hashed: `/SYSTEM/START` is
316,161 B `505F861B…` (the `--exitscreen` build) and `/ALTEREGO/AlterEgoGS.S16` is 313,376 B
`0F24BDE5…` (the default build, the same bytes as `build/AlterEgoGS`), so each disk carries the
behaviour it should.  The `.po` is **not** a release asset (`npm run make:po` remains a local
convenience); the release is the two `.2mg` images.

`npm run test` on the committed boot disk: PASS, title after 5.5 s, Level 1 after 2.3 s, same pixel
signatures as before, and the image was byte-identical before and after the run (`4115CB7F…`).

One thing to watch: the image GSplus had been playing had `ae.prefs` written into it by the guest
(`Free : 494`, `File : 16`, SHA256 `7A4DAA00…`), so the tracked copy was restored with `git checkout`
before it was published — a *played* disk is not the shipped disk.

## 2026-11-04d — Q on the 800 KiB boot disk: a real exit screen

**Q → Y** on the boot disk now ends the game for good and leaves a screen that says so, instead of
restarting it.  The user asked for a meaningful exit rather than the Win95 "now you can turn off your
computer" shrug, so the screen tells the truth: nothing on this disk can bring the game back, and the
reset button is the only way out.

```
ALTER EGO HAS EXITED
PRESS RESET TO PLAY AGAIN
THANKS FOR PLAYING
IT IS SAFE TO TURN OFF
```

- The screen is a 320×200 **Super Hi-Res bitmap** rendered at build time from the game's own NES CHR
  font (`scripts/make-quit-screen.mjs` → `QuitScreen.s`), so it looks like part of the game: white on
  black, the game's bold glyphs.  `QuitToExitScreen` (`Main.s`) saves the preferences, shuts the
  runtime down, loads palette 0 as black/white, zeroes the SCB bytes, copies four bands of text rows
  (5,120 bytes — the full picture does not fit in the tile-data bank, and an S16 file must keep its
  eight segments) and halts.  `build.js --exitscreen` builds it, and `npm run make:boot` packs that
  copy as `/SYSTEM/START`.
- A **40-column text screen** came first and was abandoned after measuring it: the legacy display does
  come up and the page does get written, but the video generator reads that page with an offset and a
  stride that do not match a plain 40×24 Apple II page (rows permuted, shifted ~6 columns left and ~2
  rows up), and neither `$C00C`, a fresh `$C029`, shadow off, both banks filled, nor zeroed
  `$C04A-$C04D` changed it.  The pixel order of the Super Hi-Res word was not guessed either: a
  throw-away build rendered four candidate orders, one per row, and only one read as text.
- Verified with a dev build that quits at start-up (`--autotest`, no key press needed): the screen
  renders exactly as above and stays up.  `npm run test` on the shipped image still passes (title
  after 9.8 s, Level 1 after 2.3 s).  And the real key path is confirmed by the user, who pressed
  Q → Y in GSplus on `build/AlterEgo.2mg` and got the exit screen (the harness's `q` does not reach
  GSplus here, so that press could not be automated).
- Artifacts: `build/AlterEgo.2mg` `4115CB7F…` (819,264 B, 1,600 blocks, 495 free);
  `build/AlterEgoGS` unchanged (`0F24BDE5…`, the default build reproduces byte for byte);
  `build/AlterEgoGS.exit` `505F861B…` (local); `build/AlterEgo-full.2mg` unchanged.
- Removed the abandoned experiment (`Bye8.s`, `dist/BYE8`, `scripts/make-bye8.mjs`), updated
  `.gitignore` (`QuitScreen.s` is generated), and the boot disk's `README.TXT` now says Q ends the game
  and only the reset button starts it again.

## 2026-11-04c — Q on the 800 KiB boot disk restarts the game

On the 800 KiB disk there is no Finder, so **Q → Y** handed the machine back to GS/OS with no next
application to run: it stopped on `Can't run next application. Error=$1E06` and sat on that screen.
Q now does what the disk can do: it saves the preferences and restarts the game.

- One source tree, **two builds**.  `build.js` writes the generated `QuitMode.s` and `Main.s`
  assembles `quit` from it: the default build shuts down and calls `_QuitGS` (the full System 6
  volume, back to the Finder), `build.js --boot` saves the preferences and restarts (the boot disk,
  which has no shell).  `npm run make:boot` builds the boot-disk copy itself
  (`build/AlterEgoGS.boot`, local and gitignored) and packs it, so the image cannot be built from a
  copy that quits.  `npm run build:alterego` still publishes the full-volume application as
  `build/AlterEgoGS`.
- Asking GS/OS whether the volume has a Finder was tried first and abandoned: from the game, and
  from the start-up of a program the Finder launched, `_OpenGS` failed for every candidate
  (`1/…`, `2/…`, root-relative, by volume name) even though `/SYSTEM/FINDER` is there.  On the boot
  disk the same call *does* work at start-up — `1/README.TXT` resolves, which is how prefix 1 turned
  out to be the boot volume's root — so what fails is knowing the path, not making the call.  A
  build switch cannot guess wrong.
- Verified in GSplus at `Limit: 16.0Mhz`: on `build/AlterEgo.2mg`, Q then Y returns to the title and
  the game continues (no `$1E06` screen); on a full System 6 volume with the game installed, Q then
  Y hands control back to GS/OS and it runs its start application again (no stop).  `npm run test`
  passes (title after 9.8 s, Level 1 after 2.3 s).
- `npm run test` now boots a **scratch copy** of `build/AlterEgo.2mg` in `tmp/test/` (with `s7d1`
  rewritten) instead of the shipped file, and a run leaves it byte for byte unchanged.
- The key sheet on the disk (`dist/README.TXT`) spells out both cases — on this disk EXIT GAME and
  Q (then Y) return to the title, on a full System 6 disk Q (then Y) quits to the Finder — and the
  image was repacked after the edit (`npm run test` still passes, 9.9 s / 2.3 s).

## 2026-11-04b — release boot disk is 800 KiB (`npm run make:boot`)

The release `.2mg` is now **819,264 bytes** (a 64-byte 2IMG header plus 1,600 blocks = 800 KiB)
instead of 3.5 MB: ProDOS 8, the minimal GS/OS 6 boot set and the game — no Finder, no desktop,
boot straight into the game.

- `build/AlterEgo.2mg` is generated by `npm run make:boot` (`iigs/scripts/make-boot-2mg.mjs`): it
  copies `iigs/dist/GSBoot.2mg` (the silky-gs distribution's minimal boot disk, made by that
  repository's `scripts/make-boot-disk.js`), renames the volume to `ALTEREGO`, adds the application as
  `/SYSTEM/START` (S16 `$DB03`, 613 blocks) and `iigs/dist/README.TXT` at the root as a `$B0` ProDOS
  text file.  GS/OS launches `/SYSTEM/START` at boot, and that file is the game.
- Building a minimal boot set by deleting files from the 3.5 MB volume does **not** work: the boot
  stops with error `$0046` "while loading the start PSI file".  The template is a boot set that is
  known to boot — every silky-gs game is distributed exactly this way.
- Verified: `npm run test` passes on the 800 KiB disk (title after 9.9 s, Level 1 after 2.3 s, same
  pixel signatures); GSplus reaches the title and Level 1 at `Limit: 16.0Mhz`; `cadius CATALOG` shows
  1,600 blocks, 15 files, 500 free, and `CHECKVOLUME` is clean.
- The 3.5 MB System 6 volume stays as **`build/AlterEgo-full.2mg`** (Finder desktop, game at
  `/ALTEREGO/AlterEgoGS.S16`), so both forms ship; `npm run trim` now defaults to it.  `npm run
  make:po` follows `build/AlterEgo.2mg`, so the `.po` is now 819,200 bytes (1,600 blocks).
- `iigs/README.md` and the root `README.md` describe both images; the boot disk's key sheet is
  `iigs/dist/README.TXT`.

## 2026-11-04 — boot image trimmed from 10 MB to 3.5 MB

The shipped `.2mg` carried the same System 6 volume the port had always used: 20,480 blocks
(10,485,824 bytes), of which only 6,439 were allocated.  It is now **7,168 blocks**
(3,670,080 bytes) — the smallest 0.5 MiB multiple that still holds every file.

- `npm run trim` (`iigs/scripts/trim-2mg.mjs`) rewrites the volume in place instead of repacking it:
  it walks the volume directory chain to find the allocation bitmap, reads the highest allocated
  block, then patches the volume header's total-blocks word, the bitmap bits past the new end and
  the 2IMG block count/data size, and truncates.  File data, directory entries, resource forks and
  GS/OS extended entries are untouched, so the files are the same files.
- The bitmap is ProDOS 8's (0 bit = in use), one bitmap block per 4,096 blocks: the smaller volume
  needs two, so the three blocks the old bitmap used (8-10) stay allocated; `cadius CHECKVOLUME`
  reports exactly those three as "in use but not referenced" and nothing else.
- Verified: `npm run test` passes on the trimmed image (title after 12.2 s, Level 1 after 2.3 s,
  same pixel signatures), `cadius CATALOG` still lists 185 files and 11 directories with 729 blocks
  free, and re-running the script is a no-op.
- `npm run make:po` now derives the matching 3,670,016-byte `.po`; `iigs/README.md` and the root
  `README.md` quote the new size.

## 2026-11-03 — speed guidance for release: 16 MHz baseline

Docs only; no source, `prg.bin`, `AlterEgoGS` or `.2mg` change (the artifacts are byte-identical to
2026-11-01).

- `README.md` and `iigs/README.md` now state the release baseline is **16 MHz**, with the factory
  **2.8 MHz** setting playable (about 30 fps gameplay, 2–3 minute boot) and an accelerator in between
  (a TransWarp GS at 7.1 MHz) scaling with the clock.
- Upstream triage of Lucas Scharenbroich's five suggestions, the filed silky-gs issue
  (<https://github.com/lscharen/silky-gs/issues/46>, refiled from `iigs-game-engine` issue 29 after its
  owner closed that as the wrong repository) and the decision not to re-base onto upstream `main` are
  recorded in `iigs/AGENTS.md`; the unfiled tile-renderer question is kept in
  `iigs/docs/upstream-issues/`.
- `npm run make:po` (`iigs/scripts/make-po.mjs`) derives the bare ProDOS **`build/AlterEgo.po`**
  (20,480 blocks) from the tracked `.2mg` by stripping the 2IMG header, with header/format/volume
  checks so a bad image cannot be shipped silently.  Verified booting that `.po` in GSplus: title
  and Level 1 at `Limit: 16.0Mhz`.  The `.po` is generated, not committed; the `.2mg` is the IIgs
  release and remains the source of truth.

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
  `build/AlterEgo.2mg` and `build/AlterEgoGS`, next to the VERA port's images in
  `vera/build/`.  `build.js` publishes the assembled application there, and the GSplus configuration
  (`iigs/emu/gsplus-alterego.kegs`) points at the new image.  The stale 2026-10-29 image
  (`AlterEgoOld.2mg`) was deleted.
- The boot image was renamed `AlterEgoJml.2mg` → **`AlterEgo.2mg`** and the configuration to
  `gsplus-alterego.kegs`; the `Jml` suffix was a leftover label from the earlier silky-gs tree and
  nothing inside the image depended on it (volume `/ALTEREGO`, program `/ALTEREGO/AlterEgoGS.S16`).
- `prg.bin` must stay exactly 32,768 bytes; it is reproduced byte for byte from the objects imported
  into `iigs/prg-src/` with cc65 + `ld65`, so a PRG change is rebuilt there and relinked before the
  Merlin build.
- The shipped artefacts are `build/AlterEgo.2mg` (10,485,824 bytes, SHA256 `93A3004F…`),
  `build/AlterEgoGS` (313,359 bytes, SHA256 `88281425…`) and `iigs/src/games/alterego/prg.bin`
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
  | `Q` | Quit, after a confirmation screen (Y quits, N or Escape goes back). On the 800 KiB boot disk, which has no Finder, Y saves the preferences and restarts the game instead of quitting (see 2026-11-04c) |

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
