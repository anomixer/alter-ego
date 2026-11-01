# prg-src — the NES PRG staging tree for Alter Ego on the IIgs

`iigs/src/games/alterego/prg.bin` (32,768 bytes, SHA256 `C4CB0445…`) is the NES program the IIgs
build consumes: `AlterEgo.s` links it into the AEROM bank at `$8000-$FFFF`.  It is **not** built by
the IIgs build — it comes from this cc65 tree.

Provenance: on 2026-11-01 the former staging tree `C:\dev\alter-ego\build\silky` (in the archived
upstream / Apple //e working tree) was imported here, because it was the only copy of the sources the
shipped PRG came from.  The screenshots, throw-away experiment variants (`variants/game_menu*.o`,
`variants/prg_*.bin`, …) and logs of that tree were left behind.

## Files

| Path | What it is |
| --- | --- |
| `game.c`, `game_base.c` | upstream C game logic (reference; the shipped PRG comes from the objects below) |
| `work/game_apop1.c` | the variant the shipped PRG was built from (VERA-style title menu, pause menu with EXIT GAME) |
| `work/palettes.h`, `work/credits.h` | the 16-byte `palTitleBG` / `palTitleSPR` / `palSprites` / `palWellDone` arrays and the credits text |
| `variants/game_apop1.c`, `variants/game_cow.s` | the same variant, plus the generated assembly of the Cow Level build |
| `objects/game_fixed.o`, `objects/neslib_new.o`, `objects/crt0_silky.o`, `objects/audio_silky.o` | the objects the shipped PRG was linked from |
| `objects/game_cow.o`, `objects/neslib_silky.o`, `objects/audio_*.o`, `objects/music_stub.o` | alternate links kept for reference (they do **not** reproduce `prg.bin`) |
| `neslib.h`, `memmap.inc`, `silky_shims.inc` | NES API headers and the silky-gs shim includes |
| `nes_silky.cfg`, `nes_orig.cfg` | ld65 configs (`nes_silky.cfg` is the one used) |
| `map0.h` … `map25.h`, `title.h`, `gameover.h`, `welldone.h`, `credits.h`, `tileset.chr` | level/title data the C sources include |
| `neslib_silky.s`, `crt0_silky.s`, `audio_*.s`, `music_stub.s` | the 65816 shim, crt0 and FamiTone2 harness sources |

## Rebuilding `prg.bin` (verified 2026-11-01)

The shipped PRG is reproduced **byte for byte** by this link (`C:\dev\cc65` = cc65 toolchain):

```powershell
cd C:\dev\alter-ego\iigs\prg-src
& C:\dev\cc65\bin\ld65.exe -C nes_silky.cfg -o prg.bin `
    objects\crt0_silky.o objects\neslib_new.o objects\game_fixed.o objects\audio_silky.o `
    C:\dev\cc65\lib\nes.lib
```

The result is 32,768 bytes with SHA256 `C4CB0445…`, i.e. the file the IIgs build consumes.  (Linking
`objects\game_cow.o` or reassembling the shim from `neslib_silky.s` gives a different 32,768-byte PRG
— those are historical variants, not the shipped one.)

To go back to C: compile `work/game_apop1.c` with `cc65 -Os -I . -I ..` from `work/`, assemble it with
`ca65 --cpu 6502`, reassemble the 65816 shim with `ca65 --cpu 65816` (the 6502 default rejects
`phk`/`plb`), then link as above.  The objects are kept because cc65 output is toolchain-version
dependent; the sources are here so any patch can be re-derived.

After rebuilding, copy the result over `iigs/src/games/alterego/prg.bin`, rebuild the IIgs app and
repackage the boot image (see `iigs/AGENTS.md`, "Rebuilding `prg.bin` from the C sources").

**Hardcoding warning:** `iigs/src/rom/rom_exec.s` pauses the music by writing FamiTone2's byte at NES
`$0101` (bit 7).  A new PRG can move that byte; `$0102` is another FamiTone byte and must not be
clobbered (write `$0101` byte-wide).  Re-check both after relinking.
