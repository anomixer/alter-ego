# AGENTS.md — alter-ego Apple II VERA port

## Default image is FamiTone (2026-11-03)

- `vera/build/build_a2vera.ps1` now builds the live FamiTone image by default:
  `iex (Get-Content -Raw vera/build/build_a2vera.ps1)` writes
  `vera/build/alter-ego-vera.hdv`. Set `AE2VERA_PSG_BUILD=1` for the streamed
  `alter-ego-vera-psg.hdv`; `AE2VERA_FTM_BUILD` is still honoured as an explicit
  override (1 = FTM, 0 = PSG). `AE2VERA_FTM_FLOPPY=1` builds the D1/D2 pair as
  before.
- Both release HDVs were rebuilt with the flipped default and then
  boot-checked in AppleWin before being checked in: STARTUP screen, title menu
  and Level 1 (HELLO WORLD, HUD `5` reserves and `x2` exchanges) on each, with
  `SPACE` injected as a tap. `-run-cycles <N> -screenshot-and-exit <file>`
  gives a headless capture; the FTM level-1 run used 34,000,000 cycles with
  Space sent at about 17 s. Captures live in `vera/build/shots/`
  (`ftm-startup.png`, `ftm-title.png`, `ftm-level1.png`, and the `psg-*`
  equivalents), which `/build` keeps untracked.
- The FTM target had been broken since the 2026-11-02 directory move:
  `vera/tools/a2vera_ftm_tables.py` still defaulted to the old `build/a2vera`
  path, so `ftm_pitch_table.s` landed outside `vera/build/` and the build died at
  `ca65`. The script now passes `"$work\ftm_tables.h"` and
  `"$work\ftm_sfx_data.s"` explicitly, and the Python default points at
  `vera/build/`. Both variants were rebuilt to `RESULT: OK`: FTM 40 files / 438
  blocks used, PSG 51 files / 617 blocks used, and `cadius CHECKVOLUME` passes on
  both images. The checked-in release HDVs were then replaced with these
  rebuilt volumes (see the bullet above).
- `vera/tools/a2vera_windows.ps1` was stale after that move: it still defaulted
  to the PSG image, and `Capture-AEFrame` scanned only `vera/build` for `*.bmp`
  even though current AppleWin writes `AppleWin_ScreenShot_*.png` into its
  working directory. The default is now `alter-ego-vera.hdv`, and the scan
  covers both `vera/build` and `vera/build/shots` for `*.png` and `*.bmp`.

## Directory layout (2026-11-02)

- The repository root now mirrors upstream `avshabanov/alter-ego` again (the same `Makefile`, `src/`,
  `LICENSE` and `.gitignore`; only `README.md` differs), so the NES build is upstream's and `src/`
  no longer carries Apple //e changes.  Every VERA file moved one level down:
  `src/a2vera/` → **`vera/src/a2vera/`**, `build/a2vera/` → **`vera/build/`**, `tools/` →
  **`vera/tools/`**, `docs/` → **`vera/docs/`**, `AGENTS.md` → **`vera/AGENTS.md`**,
  `THIRD_PARTY_NOTICES.md` → **`vera/THIRD_PARTY_NOTICES.md`**, `1.png` / `2.png` → **`vera/`**.
- `vera/build/build_a2vera.ps1` locates the root two levels above itself and keeps using the shared
  upstream `src/` (`-I "$root\vera\src" -I "$root\src"`), so `music_title.s` and the music modules
  resolve to the VERA fork in `vera/src/` first and to upstream's `src/` second.  `title.s`'s
  `.incbin` paths and the Python/mjs tool roots were rewritten for the new depth, and the build was
  rerun to `RESULT: OK` (51 files, 983 free blocks) after the move.
- The paths quoted in the dated entries below are the pre-move (`src/...`, `build/a2vera/...`)
  names; they are kept as historical labels.  Ignore rules for the port now live in
  `vera/.gitignore` (the root `.gitignore` is upstream's), which tracks the builder plus the four
  release images and ignores the rest of `vera/build/`.

## Repository name (2026-11-01)

- This repository was called `alter-ego-vera` while VERA was the only Apple II target.  It is now
  **`alter-ego`**, because it also hosts the Apple IIgs port under `iigs/`; the local checkout is
  `C:\dev\alter-ego`.
- Release image filenames keep their `alter-ego-vera*` names (`alter-ego-vera.hdv`,
  `alter-ego-vera-psg.hdv`, `alter-ego-vera-D1.po`, `alter-ego-vera-D2.po`): they are artifact names,
  not the repository name, and renaming them would break the documented release paths.
- The VERA regression scripts under `vera/tools/` still hardcode `C:\dev\alter-ego\...` (their historical
  location).  That path is now the actual checkout, so they work again; keep that in mind if the
  checkout ever moves.

## Release image names (2026-10-14)

- The live FamiTone release uses `vera/build/alter-ego-vera.hdv`.
  Its optional dual-floppy images are `alter-ego-vera-D1.po` and
  `alter-ego-vera-D2.po` in the same directory.
- The streamed PSG release uses `vera/build/alter-ego-vera-psg.hdv`.
  Keep `-psg` on this variant only. The default build command now builds the
  live FamiTone variant; set `AE2VERA_PSG_BUILD=1` for PSG (see the 2026-11-03
  note above). The PSG STARTUP prints `PSG VER` at the right end of its title
  line; the FTM title omits it.
- Both HDVs are file-level 800 KB ProDOS volumes. A file-level install copies
  every file from one chosen image to the root of another ProDOS volume, then
  boots that volume and runs `STARTUP`. Keep all files from a build together;
  PSG needs its `.PSG` files and `SFXBANK`, and FTM needs its overlays/data.

## FTM dual-floppy release (2026-10-14)

- `vera/tools/a2vera_ftm_floppy_pack.mjs` extracts the built FTM HDV, replaces
  `STARTUP` with `vera/src/a2vera/startup_floppy.bas`, and packages two 140 KB
  ProDOS `.po` images. Use `AE2VERA_FTM_BUILD=1` plus
  `AE2VERA_FTM_FLOPPY=1` with `vera/build/build_a2vera.ps1` to build all
  three FTM artifacts. The two `.po` images are tracked release artifacts.
- D1 (`ALTER.EGO`) contains ProDOS, BASIC.SYSTEM, STARTUP, both Slot 2/4
  game binaries and both music overlays. D2 (`ALTER.EGO.2`) contains all 26
  levels, TILES, CREDITS, palettes, ending/game-over art, and the `D2READY`
  text marker. The floppy
  startup BLOADs music from D1, changes the ProDOS prefix to D2, then BRUNs
  the selected game binary by its absolute D1 pathname. Subsequent relative
  asset opens therefore read D2. Before BRUN, STARTUP opens D2READY and shows
  `PLEASE INSERT DISK 2 IN DRIVE 2` with a key-to-retry loop if D2 is absent.
  Mount D1/D2 simultaneously in Drive 1/2 of
  the same Disk II controller; the HDV remains the file-level install path.
- Both volumes pass Cadius `CHECKVOLUME`: D1 has 79 free blocks and D2 has 34
  after adding the marker file.
  AppleWin with Slot 2 VERA reached Title and Level 1 from these disks; Slot
  4 also reached a playable level. The integrated build returned `RESULT: OK`.

## Current build status (2026-10-14)

- Version choice: recommend PSG when the priority is sound closest to the
  NES and 60 Hz display updates. Recommend FTM when the priority is compact
  original FamiTone data decoded live to VERA PSG with steady in-game music.
  FTM's live decoding uses more CPU and renders about 40 display iterations/s;
  do not describe it as having a higher graphics frame rate than PSG.
- Both `alter-ego-vera-psg.hdv` and `alter-ego-vera.hdv` are playable,
  user-accepted builds. The FTM build is no longer an experimental prototype;
  it plays the original FamiTone modules directly through VERA PSG and uses
  fewer disk blocks. The FTM build is now the default output of the builder
  (2026-11-03); PSG is opt-in with `AE2VERA_PSG_BUILD=1`.
  Both now silence music while loading a level; normal gameplay playback is
  steady. Historical experiment notes below record the development process
  and do not describe current release status.

## Level-loading music pause (2026-10-14)

- Initial entry and restart already start their level song after loading.
  `complete_level()` now pauses a continuing song before ProDOS reads and
  level drawing, then resumes it from the same position after the scene and
  OAM are ready. When the next level uses a different theme, the new song
  starts after drawing instead of before it. The loading interval is
  intentionally silent so missed VSYNCs do not produce uneven notes.
- FTM and PSG HDVs and the FTM D1/D2 pair rebuilt with `RESULT: OK`.
  AppleWin checks passed for initial Level 5 entry, the new-theme Level 5 to
  6 transition, and the same-theme Level 6 to 7 transition on both variants.
  The FTM Level 7 fall and clear regression also passed.

## FTM gameplay theme order (2026-10-14)

- The native FamiTone directory in `vera/src/a2vera/fami_modules.s` aliases slot 3
  to the Level 2 module at slot 2. Gameplay had selected slots 1, 2, 3, 4,
  5, repeating the second theme for Levels 11-15 and omitting Level 5.
  `level_music()` now selects 1, 2, 4, 5, 6 for level groups 1-5, 6-10,
  11-15, 16-20, 21-25. The PSG sequence remains 1, 3, 4, 5, 6.
  The FTM sound test already skips the duplicate slot and is unchanged.
  AppleWin confirmed native song indices 1, 2, 4, 5, 6 at the five group
  boundaries, and Level 24 reported song 6.

## Falling exchange and sound-test labels (2026-10-14)

- FTM advances one or two NES steps per display iteration. At an eight-pixel
  fall boundary reached on the first of two steps, it checked item pickup but
  immediately began the next fall without accepting the exchange button.
  The shared tile-action check now handles pickup and exchange at that
  intermediate boundary. AppleWin Level 24 started at x=40,y=160 with six
  exchanges; moving right into the fall and pressing J spent one exchange and
  activated the swap before death. PSG passed the same route. FTM falling
  item regressions on Levels 7 and 10 passed; the Level 7 route cleared.
  `vera/tools/a2vera_ftm_fall_test.ps1` accepts `AE_FALL_TEST_LEVEL=24` for this
  exchange regression.
- M/N in T sound-test mode now redraw the title's MUSIC and SOUND rows as
  soon as their mute flags change. AppleWin screenshots confirmed both OFF
  labels while the SFX/BGM selector remained open on FTM and PSG.
- To make room for the FTM exchange check, its 21-byte item-base table moved
  into FTM high BSS and the 21-byte particle state moved into FTM extra BSS.
  Current map: main BSS `$6347-$674B` (FTMDATA starts `$6750`), extra BSS
  `$8400-$84FC` (phase table starts `$8500`), and high BSS `$93A0-$94B4`
  (C stack lower bound `$94C0`).

## Menu audio timing repair (2026-10-14)

- Follow-up: Left/Right already changed the music/sound mute flags, but the
  optimized title renderer did not mark the labels dirty. The selected row
  therefore kept showing `MUSIC ON` or `SOUND ON` after switching off.
  `vera/src/a2vera/main.c` now redraws the audio labels on either toggle.
  `vera/tools/a2vera_menu_test.ps1` passed on both FTM and PSG; AppleWin captures
  confirmed `MUSIC OFF` and `SOUND OFF` on the FTM title. The FTM title ran at
  59.8 iterations/s idle and 60.8 while navigating; pause ran at 60.5/s.
  Both HDVs and the FTM D1/D2 pair were rebuilt and pushed in `aa90a6d`.
- Title Up/Down now changes only the old/new row palette attributes; text is
  redrawn only when the level number or audio option changes. Pause redraws
  sprites only on cursor moves and 16-frame blink edges. The FTM player skips
  PSG register rendering while paused; the pause cue gets its first SFX tick
  before the menu repaint. AppleWin FTM menu regression measured 60.5 title
  iterations/s idle, 60.1 while navigating, and 60.7 pause iterations/s.
  FTM and PSG menu regressions passed. The FTM Level 7 fall regression still
  clears the level and advances to Level 8.
- At this checkpoint FTM HDV, FTM D1/D2, and PSG HDV rebuilt with `RESULT: OK`.
  FTM main BSS ended at `$6733` before FTMDATA `$6750`; scratch BSS occupied
  `$8400-$84E7`, before FTMTABLE `$8500`. The OAM shadow moved to
  `$93A0-$949F`, below the C stack's `$94C0` lower bound. The current layout
  is recorded above. FTM D1 had 79 free blocks; D2 had 34. FTM HDV had 438
  blocks used; PSG HDV had 617.

## Confirmed playback behavior (2026-10-14)

- The user tested both PSG and FTM images before the level-loading pause:
  music briefly hesitated during entry or level-clear transitions, while
  normal gameplay remained steady. The loading pause above replaces that
  uneven playback with deliberate silence; it has passed emulator transition
  checks but still awaits a listening check.
- The user also confirmed the landing-item pickup correction below works.

## Landing-item pickup ordering (2026-10-14)

- A second FTM edge case occurs while falling through multiple items: a
  two-step display iteration can finish one eight-pixel fall and immediately
  begin the next before the outer loop checks the crossed item cell. The
  shared item collector now runs between those two source ticks whenever a
  tile boundary is reached. This applies to every FTM level; the PSG
  one-step path remains unchanged. AppleWin regression
  `vera/tools/a2vera_ftm_fall_test.ps1` passed on Level 7's two mirrored item
  stacks, cleared Level 7, and advanced to Level 8; it also passed Level 10's
  four-item vertical stack. The test starts from the
  title and uses debugger RAM writes to select the level and position the player above each
  stack. FTM HDV/D1/D2 and PSG HDV all rebuilt with `RESULT: OK`.
- The FTM builder saves `game-ftm.dbg` so the fall regression still uses
  matching symbols after a PSG build. See the current memory map above.

- In the FTM build, one display iteration advances one or two NES-time steps.
  If an eight-pixel fall finished on the second step, the pickup check at the
  start of that iteration had been skipped while `player_fall_steps` was still
  nonzero. The same iteration could then accept Left/Right, moving the player
  off the landing cell before its item was tested.
- `vera/src/a2vera/main.c` now blocks movement for that iteration when a fall was
  still active at its start. The next iteration checks both Egos' item cells
  before input, matching the NES ordering. The PSG path retains its existing
  behavior because a single fall step still reports `falling` on that frame.
  FTM and PSG Slot 2/4 images rebuilt with `RESULT: OK`; FTM game BSS ends
  at `$673A`, below FTMDATA at `$6750`. The user confirmed pickup works.

## FTM title tempo root-cause repair (2026-10-14)

- The preceding 7/12 to 9/12 tick adjustment was audible but insufficient:
  `src/music_title.s` also had a FTM-only row speed of `$0A` instead of the
  original `$07`. Those two slowdowns multiplied. Title and sound-test BGM 00
  now use the original seven-tick row and one FamiTone source tick per VSYNC.
  AppleWin previously measured roughly 61 title display iterations/s; this
  restores the source's 60 Hz beat clock. Level tracks retain their separate
  1.5-tick game-loop schedule. The FTM Slot 2/4 HDV rebuilt with `RESULT: OK`;
  inspecting the packed `AE2VERA2` binary found song 0 at `$69A9` with its
  row-speed byte at `$69B5` equal to `7`. Live AppleWin measured 121 title
  display iterations over two seconds; the user confirmed this tempo is right.

## FTM game-speed repair (2026-10-14)

- The current FTM image replaces the C loop over eleven music envelopes with
  `vera/src/a2vera/ftm_envelopes.s`. Its scratch ZP is `$9A-$9F`, above the
  linkers' `$80-$99` ZP allocation. The overlay map places its entry at
  `$1952`, with envelope state at `$9324`; music and the native FamiTone SFX
  streams stay resident in RAM, with no gameplay audio disk reads.
- The faster player lets Level 1 run about 40 display iterations per second.
  FTM-only game logic and SFX now alternate two and one NES-time steps per
  iteration. Live AppleWin measurements: 185 logic frames in three seconds
  idle (61.7/s), 63 in one second while moving. This also returns movement
  and the Level Clear SFX stream to approximately their 60 Hz NES cadence.
  The PSG build uses its original one-step path.
- Level music alternates two and one FamiTone source ticks per game iteration.
  Title and sound-test BGM 00 run one source tick per VSYNC at the original
  seven-tick row speed, as verified above. The T sound test keeps one source
  tick per VSYNC for BGM 1-7. The user accepted the FTM build after gameplay
  and listening checks.
- The FTM Slot 2/4 HDV rebuilt with `RESULT: OK`; the linked game BSS ends
  at `$6734`, below FTMDATA at `$6750`. Both FTM and PSG build checks should
  be repeated after any further timing edits.

## PSG gameplay audio disk-I/O fix (2026-10-14)

- The PSG build now incrementally copies the 5,760-byte `SFXBANK` to VERA VRAM
  `$E000-$F67F` while the title is active. This region is below `$10000` tile
  storage and does not overlap the two 20 KB BGM buffers (`$04000` and
  `$09000`). SFX start/tick read only the cached VRAM bank; they never open,
  seek, or read ProDOS files during gameplay.
- Each VSYNC advances SFX preload by at most 256 bytes. Changing the title's
  Start Level number performs no BGM disk access. Only after Start is confirmed
  is that level's BGM prefetched in 256-byte chunks during the 50-frame start
  transition. Level-clear prefetch remains unchanged.
- A short pause may occur as a level is loaded and its BGM is made ready. Once
  play is underway, music events and SFX come from VERA VRAM; the normal game
  loop does not access disk for audio. If music was muted through level entry,
  unmuting can still load the requested song and briefly pause.
- Rebuild and inspect the PSG disk before claiming the fix complete. Historical
  entries below that describe the former SFX disk stream are superseded by this
  section.

## FTM title music looping (2026-10-14)

- The title module's four audible channel streams previously ended in a 63-row
  hold and jumped back to that same terminal hold, leaving the title silent
  after one play. Each stream now jumps back to its channel start immediately
  after its ending note tail, so the title theme repeats without the long
  silent interval. Rebuild the FTM image with `AE2VERA_FTM_BUILD=1`.

## FamiTone-to-VERA development history (2026-10-13)

The entries in this section are historical checkpoints. The current status is
summarized at the top of this file.

- PSG SFX follow-up (2026-10-14): user reported SFX 9, 11 and 12 still silent
  in the T sound test. Restored the known-good 32-byte ProDOS stream to voices
  4/5, kept one SFX tick per gameplay frame, then fixed the actual inaudibility:
  the noise period formula put SFX 11/12 at infrasonic pitch and each was only
  one active frame. The converter now uses the NES noise-period table and
  sustains those cues for four frames; SFX 9's triangle envelope is boosted
  3x. Regenerated all SFX streams and the PSG image (`RESULT: OK`); user
  listening check is pending. Level clear uses SFX 14, not `CLEAR.PSG`.
- FTM sound-test correction (2026-10-14): match PSG's BGM 00-07 range and
  remove the duplicate entry. Map is `{0,1,2,4,5,6,7,8}`: title, Level 1,
  the formal Level 2 theme, Levels 3-5, Game Over, ending. The FamiTone
  directory's index 3 is a duplicate of index 2 and is skipped. The corrected
  FTM disk rebuild passed (`RESULT: OK`); user confirmed the selector is right.

- Renamed the default PSG disk image to
  `vera/build/alter-ego-vera-psg.hdv`; `vera/tools/a2vera_title_pack.mjs`,
  `vera/tools/a2vera_windows.ps1`, README and current deliverable references use
  the new name. The build recreates it successfully (`RESULT: OK`).
- User clarified the original NES uses Level 2 Alt. PSG gameplay now selects
  indices `[1,3,4,5,6]`, and its BGM 02 test choice maps to index 3
  (`LEVEL2ALT.PSG`). At that checkpoint FTM incorrectly kept native indices
  `[1,2,3,4,5]`; its second theme
  is the original `music_level2_module` at index 2. FTM BGM 02 already selects
  that module. Both images rebuilt (`RESULT: OK`); listening comparison was
  not performed. The FTM directory aliases indices 2, 3 and 9 to the single
  original Level 2 module. FTM sound test maps its eight entries in NES order
  and skips duplicate directory index 3.
- Startup BASIC help now includes `SOUND MUTE : N` below the music mute
  control and `SFX/BGM TEST : T`. N mute and T sound-test
  controls share the same `main.c` implementation in PSG and FTM builds;
  PSG `music.c` provides the matching playback APIs. Both disk images were
  repacked with these startup instructions (`RESULT: OK`).
- `N`/`n` now toggles `sound_muted` and calls `sfx_mute()`, matching the
  title SOUND ON/OFF option. It uses its own held-key latch, resets on IIe
  key release or a cleared II+ key strobe and at level/title input reset,
  and marks the title menu dirty so its label updates. The same II+ strobe
  rearm also lets `M` toggle again. README controls updated.
- Follow-up after user reported T-menu BGM 0 slower than the title: T now
  routes an actually playing song 0 through the same `music_tick()` entry
  as the title. It tracks the playing song separately from the selector,
  so moving the BGM cursor does not change the tempo of the previous song.
  Only other songs use `music_tick_realtime()` in T mode. FTM HDV rebuilt
  (`RESULT: OK`); per user request, no emulator/listening test was run.
- T sound-test BGM 1-7 tempo corrected after the user confirmed BGM 0 and
  ESC behavior. The T loop runs once per VSYNC, but `music_tick_impl()`
  advances level songs 2.4 FamiTone source ticks per call to compensate for
  the slower gameplay loop. T now calls `music_tick_realtime()` through the
  FTM overlay's `$1006` entry, advancing exactly one source tick per VSYNC;
  title/gameplay keep their previous paths. The extra player code moved
  SFXDATA from `$1C30` to `$1C32` (linker map end `$1FF3`). FTM HDV rebuilt
  with `RESULT: OK`. Per user instruction, no AppleWin or listening test was
  performed; user tempo confirmation is pending.
- Sound-test title corruption fixed: entering the T menu called
  `set_title_prompt(0)` a second time after drawing the four title options.
  That routine clears the original PRESS START map cells, which now overlap
  START LEVEL and MUSIC ON, leaving a black block through their glyphs.
  The second call is removed; the initial call before `draw_title_menu()`
  still clears the old prompt. Rebuilt the FTM HDV (`RESULT: OK`) and entered
  T in AppleWin Slot 2. `vera/build/shots/soundtest_prompt_fix_later.bmp`
  shows both option labels intact with the SFX row below SOUND.

- Previous pause point: The slow/incorrect
  Level 1 sample exposed an actual memory collision. ProDOS OPEN's fixed buffer
  needs 1 KB, but the FTM build placed it at `$8400`, overwriting the lower
  half of the period-to-VERA phase table at `$8500`. The first Level 1 pulse
  note 28 decoded with volume 15 yet produced phase zero. FTM-only main I/O
  buffer now uses `$0C00-$0FFF`; music overlay begins at `$1000`. AppleWin
  register trace now confirms the first Level 1 chord has pulse phases 886
  (330 Hz) and 527 (196 Hz), triangle phase 705 (263 Hz), all at volume 63.
  Title playback was confirmed correct by the user. The experimental FTM HDV
  built with `RESULT: OK` and reached a rendered/playable Level 1 after this
  change. The unchanged stable `.PSG` HDV remains the release image.
- Latest user listening feedback: title too fast, Level 1 slightly slow, SFX
  inconsistent or missing. The current unreviewed build changes the VERA title
  module row speed from 7 to 10, advances Level 1 music at 2.4 ticks per
  gameplay loop, and advances the SFX interpreter twice per gameplay loop.
  Title/menu/transition SFX remain at their one-tick-per-VSYNC pace. The SFX
  parser counts repeat commands as FamiTone does (`command - $10`); initial
  pulse/noise control bytes are `$30`. Build passed; AppleWin is left running
  in the game for listening. User confirmation is pending.
- The sound-test screen's direction controls now use rising-edge input: one
  press changes one item/list, and holding a direction no longer repeats every
  frame. Its edge helper reuses the pause-menu direction byte. FTM main code
  builds with `-Os` because this image's fixed FTM data leaves only about 22
  bytes between the game BSS and audio data; the stable PSG build keeps its
  existing optimization flags. Rebuilt the FTM HDV with `RESULT: OK`.
- FTM SFX root cause fixed: `sfx_read_byte` used `lda $0000`, which ca65
  assembled as two-byte zero-page `A5 00`. The self-modifying high-byte patch
  therefore overwrote the following `RTS`, corrupting the stream and sending
  execution to `$0000`. Its placeholder is now `$FFFF`, forcing three-byte
  absolute `LDA`. Sound-test K/PAD_B is edge-triggered too, so a held K does
  not restart the selected effect each frame.
  `python vera/tools/a2vera_ftm_sfx_verify.py all` executes the linked 6502 image:
  all 15 original effects write active
  PSG voices and terminate. Rebuilt the FTM HDV (`RESULT: OK`) and booted it
  in AppleWin Slot 2. During a held K on SFX 00, live SFX pointer moved from
  `$1D51` at 100 ms to `$1D5C` at 400 ms. Host audio capture was unavailable
  because this session has no Windows output endpoint; user listening remains
  the final timbre check. The regular PSG HDV also rebuilt with `RESULT: OK`.
  The FTM image was rebuilt again afterward; AppleWin PID 9836 is left at
  `SFX 00 BGM 0` for listening.
- User confirms FTM SFX now sound. Latest request raised their loudness: the
  per-level VERA gain curve is about 20% higher, capped at `$3C` (60/63), up
  from `$30` (48/63). FTM image rebuilt with `RESULT: OK`. AppleWin PID 11776
  is at the SFX test menu for listening confirmation. The SFX test row and
  its three value sprites now render at y=216, directly below the title's
  SOUND row at y=200; rebuilt the FTM HDV and verified the screenshot.
- Level 1 tempo had been about 0.53 s between 0.333 s reference beat events:
  FamiTone was ticked once per roughly 30-38 Hz game loop. The FTM runtime now
  advances two source ticks per game iteration, plus one tick every five loops,
  and sends one consolidated VERA register update. Title song 0 retains one
  tick per iteration with row speed 8. AppleWin timestamped register trace of a
  previous build
  showed the characteristic Level 1 noise onset intervals around 0.312-0.390 s
  (typically 0.328-0.360 s); speed is close but not yet listener-approved.
  Fast NES noise periods now clamp to VERA's `$FFFF` phase word, matching the
  stable converter's Level 1 noise. Noise loudness is still a listening item.
  SFXDATA is now `$1C30` (its exact derived addresses are regenerated by
  `vera/tools/a2vera_ftm_sfx.py`); music BSS remains `$9300`, phase table `$8500`.
  Do not reuse the obsolete `$8400` main buffer layout or earlier MP3 verdict.
- Earlier 2026-10-13 Level 1 audio repair (superseded layout): the music overlay's SFXDATA moved from
  `$1C00`, but the separately linked SFX interpreter and generated period
  tables still read the old addresses. `vera/tools/a2vera_ftm_sfx.py` now derives
  every address from `vera/src/a2vera/music_ftm.cfg` and emits one layout include
  for the game binary. SFXDATA starts at `$1C10`, ends at `$1FD1`, and the
  exported table addresses are `$1C10/$1C2E/$1D0A`. FamiTone rest notes
  (`note 63`) now zero the VERA channel volume as well as frequency; previously
  they produced sustained DC and pops. NES 75% pulse duty now maps to VERA 25%
  duty, its phase-inverted timbral equivalent. Full 45-second AppleWin VERA
  core capture is `vera/build/shots/ftm_level1_long.wav`; the 30-second
  Level 1 excerpt is `ftm_level1_repaired.mp3`. Screenshot
  `ftm_repaired_game.bmp` confirms the game remained active after the capture.
  The user rejected this older recording; use the rebuilt HDV above.
- 2026-10-13 earlier tonal audio fix: the live player's tonal instrument pointers were
  incorrectly rotated. `src/music_instruments.s` and `src/famitone.s`
  establish the order as volume, note offset, pitch offset; the C player
  previously read offsets 2, 4, 0 for pulse/triangle, leaving those voices
  effectively muted while noise remained audible. `load_instrument` now uses
  offsets 0, 2, 4. Triangle also uses half the pulse phase for the same NES
  timer period. The music overlay previously placed SFXDATA at `$1C01` but
  this left stale hardcoded SFX addresses. Rebuilt FTM HDV reports `RESULT: OK` and AppleWin
  reached Level 1 without BRK. Direct VERA-core title stems (1-second RMS at
  second 16): pulse 1 0.0251, pulse 2 0.0263, triangle 0.0328, noise 0.0119.
  Level 1 at second 16: 0.0343, 0.0266, 0.0420, 0.0047. Full captures and
  listening samples: `vera/build/shots/ftm_title_fixed_full.wav`,
  `ftm_level1_fixed_full.wav`, `ftm_title_fixed.mp3`,
  `ftm_level1_fixed.mp3`. The user found that first Level 1 sample unacceptable;
  use the later `ftm_level1_repaired.mp3` for evaluation.

- Stable `vera/build/alter-ego-vera-psg.hdv` remains the release image and still
  uses `.PSG` streams. The separate experimental image is
  `vera/build/alter-ego-vera.hdv`. Rebuild it with:
  `$env:CC65_BIN='C:\dev\cc65\bin'; $env:AE2VERA_FTM_BUILD='1'; iex (Get-Content -Raw vera\build\build_a2vera.ps1)`.
  It is a separate target in the same builder/packer; `--ftm` makes the packer
  omit all converted music/SFX bank files.
- `vera/src/a2vera/ftm_player.c` is a new VERA PSG FamiTone v1.24 player; use
  `src/famitone.s` only as the original NES format/timing reference. Do not
  adapt or reuse the AY-output implementation in `src/a2/ftm.s`. The user
  supplied [REA](https://github.com/morluto/rea), an agent-based reverse
  engineering toolkit; it is not needed for this path because the game and
  FamiTone player source are available locally.
- FamiTone data for the eight game-used songs is 6,733 bytes including the
  20-byte pointer directory. The period-to-VERA phase table is 3,548 bytes.
  Cadius reports 430 used blocks in the FTM image vs 613 in the stable image:
  183 fewer blocks (93,696 bytes allocated) and 11 fewer files.
  The live player plus support code links to the full 4 KB `$1000-$1FFF`
  music overlay (binary 4,095 bytes); music state is `$9300-$9394`. The main
  game image is 29,184 bytes from `$2000` through `$91FF`. Current FTM layout:
  compact SFX code/state is `$819D-$83D4`, current main ProDOS I/O buffer is
  `$0C00-$0FFF`, and phase table is `$8500-$92DB`. The cc65 C stack starts at
  `$9600`, leaving 805 bytes below it. Recheck map addresses after every build.
- Full rebuild passed at 2026-10-13 00:06. It fixed two PSG register bugs:
  frequency high byte was truncated to two bits, and NES 4-bit envelope volume
  was incorrectly duplicated instead of mapped to VERA's 6-bit gain. Noise
  notes now include the FamiTone instrument offset and use the NES APU period
  table, capped at VERA's fastest representable rate.
  AppleWin 1.32.1.0 booted the rebuilt image on enhanced //e with Slot 2 VERA;
  title and Level 1 rendered. A 4-second Remote Audio loopback capture was
  silent for both this image and the unchanged stable image, so this host's
  capture path cannot confirm audibility or track fidelity. Noise's fastest
  periods exceed VERA's frequency range; compact test SFX do not reproduce the
  original 15 FamiTone effects. Do not replace the stable image until audio is
  compared against NES.
- The game uses title, levels 1-5, game over and congratulations; Level 2 Alt
  is the game's second theme, while the separate Level Clear song is unused.
  The source FTM has ten songs; level clear remains source SFX 14. VERA output uses control bits 7:6 for
  stereo, 6-bit volume mapped from the NES 4-bit envelope with a 2x gain curve,
  pulse width in
  bits 5:0, triangle `$80`, and noise `$C0`.
- `Simpl0r.ftm` has ten songs; the game uses title, levels 1-5, game over and
  congratulations. Level 2 Alt is the second level theme; Level Clear is
  unused and clear is SFX 14.
  The embedded modules are the original FamiTone v1.24 data, not FamiStudio
  FamiTone2 output. VERA gain maps the NES 4-bit envelope to its 6-bit volume;
  stereo is in control bits 7:6, pulse width in bits 5:0, triangle uses `$80`
  and noise `$C0`. FTM-specific noise
  pitch and audible output still need comparison against the NES.

## Current verified VERA runtime (2026-10-12)

- Latest title and pause menus: title choices are START GAME, START LEVEL,
  MUSIC ON/OFF, SOUND ON/OFF at rows 19/21/23/25 from the same left column;
  the 8x8 level digits are vertically centered beside the 8x16 START LEVEL
  label.
  Redrawing clears the full 12-cell text span first, preventing stale trailing
  letters (for example, MUSIC OFF becoming MUSIC ONF). Pause adds EXIT GAME;
  choosing it returns to the title with gameplay sprites and keyboard state
  reset. `vera/tools/a2vera_menu_test.ps1` verifies audio toggles, level selection,
  pause Exit, and return to title. AppleWin test passed after the text-clear fix.
- `title_screen()` now clears VERA OAM and its shadow table on entry. The
  all-level ending leaves its animated actors in OAM, so returning from the
  ending previously showed those actors beside the title menu. Rebuilt the
  800 KB image (`RESULT: OK`) and reran the AppleWin menu regression; it passed.
- Music conversion now applies a 2.0x amplitude gain through VERA's logarithmic
  volume table (about +6 dB per voice through the useful range, with peaks
  capped at 63). Offline `psgplay` render of Level 1 measured +3.11 dB RMS
  against the previous checked-in stream. One-shot effects are written to
  paired VERA voices 4 and 5 for about +6 dB. Effect shutdown silences both
  voices; music keeps its existing mute/pause behavior. Build and title-menu
  regression pass; gameplay measured 60.60 updates/sec. The automated normal
  collection route did not reach LEVEL CLEAR in this run, so full-level
  gameplay still needs confirmation.
- Starting from START GAME or START LEVEL now flashes the selected row on/off
  every four frames during the NES-matched 50-frame start transition, then
  fades into gameplay. The START LEVEL digits flash with the label.
- Pause menu input now advances one entry per new Up/Down press (held keys or
  joystick directions do not skip entries). EXIT GAME is drawn as `EXIT GAME`
  with a single character-width space. AppleWin menu regression asserts one
  Down press leaves the cursor on RESTART.
- Music playback event buffer now holds 18 register pairs per frame. LEVEL1.PSG
  begins with 18 pairs; the old 16-pair runtime guard stopped that track on its
  first tick even though disk validation passed. Verify title and Level 1
  playback state in AppleWin when changing the stream format.

Current runtime summary. The port supports
Apple II Plus and newer slot-based Apple II models; tested targets are Apple
II+ with 64 KB (48 KB plus a 16 KB Slot 0 Language Card) and enhanced Apple
IIe, with VERA in Slot 2 or 4. Both use the base `apple2` cc65 target and
`apple2.lib`, assembled for NMOS 6502. Game pacing and startup use VERA VSYNC,
not the IIe-only `$C019` VBL register. Current build: `RESULT: OK`.
Deliverable: `vera/build/alter-ego-vera-psg.hdv` (800 KB ProDOS, volume ALTER.EGO).

### Repository-local build dependencies (2026-10-12)

- This build recipe targets Windows PowerShell: `vera/build/build_a2vera.ps1`
  uses the bundled Windows Cadius executable. Install Python 3, Node.js, and
  cc65 with its Apple II headers/libraries; set `CC65_BIN` to cc65's `bin`
  folder or add that folder to `PATH`.
- The packer no longer reads sibling repositories. Cadius 1.4.5 is bundled as
  `vera/tools/cadius.exe`; it is GPL-3.0, with source and license available from
  the upstream project. Upstream source is not vendored.
  Applesoft tokenization and PSG validation are in `vera/tools/`; the ProDOS 2.4.3
  boot image and the cc65 assembler include used by this port are under
  `vera/src/a2vera/`; converted music and SFX streams are checked in under
  `vera/src/a2vera/music_assets/`.
- Ordinary PSG and FTM builds use the checked-in music and do not need
  FamiStudio or ftmplay. Regenerating the PSG music streams manually requires
  FamiStudio (`FAMISTUDIO`) and the standalone player (`FTMPLAY`).
- `vera/build/build_a2vera.ps1` builds all 26 levels and finds the repository
  relative to its own location. From the repository root, set `$env:CC65_BIN`
  if needed, then run `iex (Get-Content -Raw vera/build/build_a2vera.ps1)`
  for the default FTM HDV. Set `$env:AE2VERA_PSG_BUILD='1'` for the PSG HDV;
  also set `$env:AE2VERA_FTM_FLOPPY='1'` to build the FTM D1/D2 floppy pair.
  See `THIRD_PARTY_NOTICES.md` for bundled component provenance.

- Workspace cleanup on 2026-10-14 removed the DHGR/DOS 3.3 prototype sources,
  diagnostic tools, emulator dumps, generated audio and build intermediates.
  The tracked VERA HDV and D1/D2 release images remain; other `/build` output is
  ignored and regenerated by the build script.
- Slot 2 and Slot 4 have separate game and music binaries compiled with the
  matching `$C200`/`$C400` VERA base. `STARTUP.BAS` probes Slot 2 then Slot 4
  and loads the matching pair.
- `STARTUP.BAS` follows the left-aligned CX16-Othello startup style: title,
  `BY ANOMIXER https://github.com/anomixer`, then the dashed separator,
  VERA status, and Alter Ego keyboard/joystick controls. It probes VERA Slot 2
  before loading the game, and shows an install error when no card is present.
  With a card, any key continues or a 300-frame VERA VSYNC countdown expires
  in about five seconds. AppleWin
  verified both detected and missing-card screens. Latest startup build:
  RESULT OK; the larger STARTUP file leaves 1023 free blocks on the 800 KB volume.
- Latest Credits change: cold boot now shows source-derived Credits before
  the title, held for the NES 150 frames (2.5 s); Space/PB1 skips it. It runs
  only on initial boot, with title music starting afterward. Original credits
  (including the upstream hacked-version author) move up five tile rows/40 px.
  New lines at rows 24/26 are `APPLE II VERA CONVERSION BY` (blue) and
  `ANOMIXER 2026` (orange), using the original NES font and palettes. Both
  begin at NES column 3 (VERA x=56), aligned with the original credits.
- `M` toggles background music mute on a fresh key press. Muting zeroes only
  the four music voice volumes; game SFX remain audible. The mute state persists
  across track changes and pause/resume, and unmuting restores the latest streamed
  music volumes. README lists the control. Build succeeded; the new input/audio
  path has not yet been exercised in AppleWin.
- Music PSG events play from VERA VRAM rather than ProDOS on each frame. Two
  20 KB song regions at `$04000` and `$09000` support active playback plus
  prefetch. During a level-clear sequence that changes tracks, the next song is
  read in 256-byte chunks and the ready buffer is selected at the transition.
  Restarting the same track reuses its existing VRAM cache. Keep SFX on the
  known-good 32-byte ProDOS stream: the attempted VRAM bank cache silenced
  effects and has been reverted. Music remains cached; SFX disk reads and
  prefetch can still consume CPU time.
  While Mute is on, track changes only update the requested track and skip
  both loading and prefetch. Turning music back on lazily loads the requested
  track if it is not already cached; that first unmute may briefly stall.
  Build passed on 2026-10-12; smoothness of the music cache/prefetch needs an
  AppleWin runtime check. VERA VRAM does not autonomously play PSG events.
- CREDITS/CRPAL are streamed from disk. The 800 KB ALTER.EGO image now contains
  51 files, with 968 free blocks (484 KB). `a2vera_art.py` generates credits
  along with ending/game-over art. Required-file checks include both assets.
- Actual AppleWin Credits map/palette and every glyph pixel matched the preview
  in `shots/credits_verified.bmp`. Both timed intro and Space skip reached the
  title, then Level 1 with five reserves. Tests: `a2vera_credits_test.ps1` and
  `a2vera_verify_credits.py`. A C209 read each intro frame is necessary for this
  fork's static-screen scanout; map/palette alone previously passed while BMPs
  were partially stale. Do not remove that read. The helper's default boot wait
  is now 10 s; `-bootWaitSeconds 2` allows observing the intro itself.
- User requested an 800 KB HDV and volume name `ALTER.EGO`. The packer creates
  1600 blocks, installs the bundled boot blocks plus PRODOS/BASIC.SYSTEM, and
  checks all required files. The current image has 51 files and 968 free blocks.
- Arrow key codes $08/$15/$0B/$0A join WASD. `input.s` reads Apple II joystick
  PDL0/PDL1 together with a centre dead zone, auto-detects a controller at boot,
  and ignores a disconnected port. G re-detects after hot-plug/configuration.
  PB0 exchanges; PB1 starts/pauses/confirms once per press. Configure AppleWin
  Joystick 1 for the actual PC controller, or NumPad for emulated port testing.
  The arrow/joystick regression is `vera/tools/a2vera_input_test.ps1`.
  Actual AppleWin tests passed all four directions, climbing, exchange, pause,
  Resume/Restart selection and spending exactly one reserve. PB1 release now
  clears its edge state without generating another Start event. Both tested
  modes measured about 58 Hz by host wall clock, with joystick polling enabled.
  Real USB hardware was not attached; the joystick tests used AppleWin's
  NumPad emulation of the same Apple II game-port registers. A separate boot
  with Joystick 1 disabled verified no phantom motion and working WASD; the
  original emulator joystick setting was restored afterward.
- 2026-10-12 keyboard behavior: `$C010` bit 7 is a valid any-key-down flag on
  IIe, but II+ returns floating-bus data there. `keyboard_pad()` identifies IIe
  from the firmware signature at `$FBB3`. On II+, a direction press is cached
  and remains active until another key is pressed; each key event reads/writes
  `$C010` to clear the keyboard latch, and each `load_level_file()` clears the
  latch and cached direction. This matches the II+ keyboard hardware, which
  does not report key release; enhanced IIe has a held-key flag and stops
  movement on release. Build passed; rerun the II+ live-input check before
  calling this behavior runtime-verified.
- Level transition brightness flash fix: `load_level_file()` now disables the
  VERA display layers while writing the map and full palette, scales the new
  palette to its fade-in starting brightness, then restores the previous video
  mode. This prevents a full-bright palette being shown for one frame before
  the fade-in drops it to 25%. Build and HDV verification passed; visual
  confirmation in AppleWin is still pending.
- Actual AppleWin cold boot, title, gameplay and ending now work. Use
  `C:/dev/applewin/release/AppleWin.exe -h1 <absolute HDV path> -s6 empty
  -s7 hdc -model apple2ee -s2 vera -no-full-screen -power-on`.
  A stale floppy can override boot; `-power-on` is required for automation.
- Three actual all-level runs loaded LV00..LV25 and reached the ending using
  the source Select cheat. Snapshot checks compared maps, both CHR banks,
  main code bytes, unused sprites and pause state. The latest run also checked
  all eight pause palette banks exactly, waiting for intro/pause rendering
  completion rather than fixed delays. These runs verify loading
  and progression; they do not prove every puzzle was solved without cheats.
- Live control tests also passed Sound Test entry/exit, five pause-menu
  restarts (reserves 4,3,2,1,0), disabling Restart at zero reserves, resuming
  the final life, and the subsequent enemy death/game-over transition. This
  matches the NES: at zero reserves Pause offers Resume only; a death on the
  final life proceeds to Game Over rather than turning Restart into an exit.
  The latest host-audio assertion was skipped because Remote Audio capture
  was silent; the earlier successful ending WAV remains the audio evidence.
- A normal first-level route collected ITEM1/ITEM2, exchanged twice, descended
  ladders and fell onto platforms, then advanced to Level 2 with five reserves
  and `level_skip=0`. Screenshot `vera/build/shots/verified_level_clear.bmp`
  shows the actual clear message. Both 20-cell name rows are erased before
  drawing/blinking LEVEL CLEAR; all 18 trailing cells were verified zero.
- Startup asset-read failure was traced to protected ProDOS buffers at $BB00/
  $BC00. `iobuf.s` now supplies aligned fixed buffers: main $8400-$87FF,
  music $8800-$8BFF, SFX $8C00-$8FFF. Main code/data/BSS stay below $8400;
  music code $1000-$1FFF, BSS $9200-$92FF; shared C stack $94C0-$95FF.
  No heap allocations are used for these disk buffers.
- Assembly OAM and cc65 static locals achieved 59.59 game updates/second in
  a measured AppleWin run (164 frames over 2,815,662 CPU cycles at 1.023 MHz).
  Movement takes eight frames per tile, including the input frame.
- Input reads the Apple keyboard latch plus VERA-independent joystick port,
  allowing WASD and exchanges on II+ and IIe. Pause/restart,
  idle collection ordering, exchange/enemy freeze, particles, death flash,
  walk/ladder poses, source RNG/stars, enemy eyes, pause palettes and fades
  have been brought closer to the NES source. Pause menu sprites are all hidden
  on resume. Palette fades use VERA RGB scaling.
- Music and SFX use separate playback state; effects no longer stop background
  music. Pause mutes/restores music voices without restarting the song. Level
  loading services audio from VERA VSYNC status while preserving VERA address
  registers.
  Actual ending audio was recorded in `shots/ending_focused.wav` (RMS 0.03072,
  peak 0.12817). Host focus/Remote Audio changes can silence WASAPI capture;
  a silent capture alone does not establish silent guest PSG output.
- Approved noise gains: title 1.2, other songs 1.0; triangle 1.25. Conversion
  remains WAV-derived, fixed-pulse-width PSG; SFX use one dominant voice.
  NES source is FamiTone v1.24, with DPCM initialization disabled and the
  exported Level 2 sample channel consisting of rests.
- Working observation tools: `vera/tools/a2vera_windows.ps1` enumerates APPLE2FRAME,
  injects input and invokes AppleWin's built-in BMP/snapshot functions;
  `a2vera_cpu.ps1` reads guest memory through the matching AppleWin PDB;
  `a2vera_snapshot.py` preserves both 64 KB VERA memory banks.
  Regression tools: `a2vera_smoke.ps1`, `a2vera_gameplay_test.ps1`,
  `a2vera_controls_test.ps1`, `a2vera_verify_runtime.py`.
- Build: `iex (Get-Content -Raw vera/build/build_a2vera.ps1)`.
  Use `AE2VERA_SKIP_ASSETS=1` only for runtime-only changes. Re-read linker maps;
  every compiler/assembler call must retain `--cpu 6502`. Latest build: RESULT OK.
  The historical hardcoded Python path is absent here; `python` resolves to
  `C:/Users/USER/AppData/Local/Python/pythoncore-3.14-64/python.exe`.
- Do not claim 100% parity: all-level loading and the physical first-level
  solution are verified, while full NES differential playthrough and exact APU
  music/effect reproduction remain open. Preserve unrelated local NES edits
  in `src/game.c` and `src/compile.bat`; stage only the intended VERA changes.

### Apple II+ 64 KB compatibility fix (2026-10-12)

- Root cause: compiling cc65/ca65 sources with `--cpu 6502` was insufficient
  while linking `apple2enh.lib`. Its runtime contained `$92` at `$508C`, a
  65C02-only opcode; the II+ NMOS 6502 jammed there before drawing the title.
  Build script now uses `-t apple2 --cpu 6502` and links `apple2.lib` for both
  game and music binaries. Do not switch these back to the `apple2enh` target
  or library.
- Replaced game `$C019` VBL polling and startup's `$C019` WAIT with VERA VSYNC
  status at slot base + `$07`, enabled through base + `$06`. Startup waits for
  300 VERA VSYNC events (about five seconds); game pacing and loading audio
  acknowledge the write-one-to-clear VSYNC bit.
- Verified AppleWin 1.32 VERA fork on II+ 64 KB using `-model apple2p -s0
  languagecard`: Slot 2 and Slot 4 both autodetect, draw the title, and enter
  Level 1 on Space. Runtime snapshot: Level 1, five lives, three items, two
  exchanges. A held Right moved the player and falling into water triggered
  death. Enhanced IIe also reached Level 1 with the same apple2 build.

## DHGR feasibility study closed (2026-10-14)

A static conversion of NES title and Level 1 screenshots retained the scene
layout but lost small text and fine detail at DHGR's colour-cell resolution.
Keeping PRESS START readable required redrawing it, which made the result a
demake rather than a faithful port. The user chose to keep the VERA version as
the Apple II target; DHGR/Mockingboard is not a release target.

The DHGR runtime sources, DOS 3.3 image work, diagnostic scripts, rendered
previews, test disks and emulator captures have been removed. Do not restore or
continue the DHGR port unless the user reopens that direction. The release
artifacts are the tracked VERA HDVs and FamiTone D1/D2 floppy images listed at
the top of this file. Rebuild them with `vera/build/build_a2vera.ps1`.
