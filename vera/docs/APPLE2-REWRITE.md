# Apple II VERA Port — runtime notes

The VERA port is the sole Apple II release target. It supports Apple II Plus or
newer compatible systems with a VERA card in Slot 2 or Slot 4. Apple II Plus
requires 48 KB plus a 16 KB Slot 0 Language Card. The game uses VERA VRAM and
the NMOS 6502; it does not require the IIe auxiliary 64 KB RAM.

## Release builds

- `vera/build/alter-ego-vera.hdv`: live FamiTone playback, 800 KB ProDOS.
- `vera/build/alter-ego-vera-psg.hdv`: streamed PSG playback, 800 KB ProDOS.
- `vera/build/alter-ego-vera-D1.po` and `alter-ego-vera-D2.po`: FamiTone dual-floppy version.

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

Set `CC65_BIN` if cc65 is not on `PATH`. Set `AE2VERA_FTM_BUILD=1` for the
FamiTone image and also `AE2VERA_FTM_FLOPPY=1` to create its D1/D2 pair. A
successful build ends with `RESULT: OK`.

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
