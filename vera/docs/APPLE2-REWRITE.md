# Apple II VERA Port — runtime notes

The VERA port is the sole Apple II release target. It supports Apple II Plus or
newer compatible systems with a VERA card in Slot 2 or Slot 4. Apple II Plus
requires 48 KB plus a 16 KB Slot 0 Language Card. The game uses VERA VRAM and
the NMOS 6502; it does not require the IIe auxiliary 64 KB RAM.

## Release builds

- `vera/build/alter-ego-vera.hdv`: live FamiTone playback, 800 KB ProDOS (the
  default build since 2026-11-03).
- `vera/build/alter-ego-vera-psg.hdv`: streamed PSG playback, 800 KB ProDOS,
  built with `AE2VERA_PSG_BUILD=1`.
- `vera/build/alter-ego-vera-D1.po` and `alter-ego-vera-D2.po`: FamiTone dual
  floppy version.

Both images were rebuilt from the flipped builder default on 2026-11-03 and
boot-checked in AppleWin (`-model apple2ee -s2 vera`): STARTUP screen, title
menu, and Level 1 (HELLO WORLD, five reserves, two exchanges) on each. The PSG
STARTUP prints `PSG VER`; the FamiTone one does not.

HDVs are file-level volumes. Copy all files from the chosen HDV to another
ProDOS volume and run `STARTUP`. The PSG release needs its `.PSG` files and
`SFXBANK`; the FamiTone release needs its music overlays and data files.
For the dual-floppy build, insert D1 and D2 in drives 1 and 2; startup checks
for D2 before launching.

## Build

Install Python 3, Node.js and cc65. The packer, Cadius, ProDOS boot files,
assembly includes and music assets are included in this repository. From the
repository root, run:

```powershell
iex (Get-Content -Raw vera/build/build_a2vera.ps1)
```

Set `CC65_BIN` if cc65 is not on `PATH`. This builds the FamiTone image; set
`AE2VERA_PSG_BUILD=1` for the streamed PSG image, and `AE2VERA_FTM_FLOPPY=1`
to create the FamiTone D1/D2 pair. `AE2VERA_FTM_BUILD` is still accepted as an
explicit override (1 = FTM, 0 = PSG). A successful build ends with
`RESULT: OK`.

## Known playback behavior

Music plays steadily during normal gameplay. It may briefly hesitate while a
level starts or clears and the next track is prepared. The PSG version may
also pause briefly when a level is first loaded.

## DHGR feasibility study closed (2026-10-14)

A static DHGR conversion of NES title and Level 1 screenshots retained the
scene layout but lost small text and fine detail at DHGR's colour-cell
resolution. Keeping the title prompt readable required redrawing it, which
made the result a demake rather than a faithful port. DHGR/Mockingboard is not
a release target. Old prototype sources and generated test artifacts remain as
local leftovers outside the supported build. Use the VERA build for Apple II
development and release.
