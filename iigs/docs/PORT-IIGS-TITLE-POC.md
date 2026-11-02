# Alter Ego — Apple IIgs / silky-gs title-screen PoC

> **路徑說明（2026-11-01）**：本文件寫於上游工作樹 `C:\dev\alter-ego` 內，文中 `build/…`、`src/…`、`tools/…` 都是那棵樹的路徑，該樹已於 2026-11-01 移除。IIgs port 的現況見 [iigs/AGENTS.md](../iigs/AGENTS.md)。


Status: **title art renders on the IIgs SHR screen** (GSplus 1.38 screenshot).
This is a proof of pipeline, not a complete port.

## What is running

- Original cc65 NES `game.c` (HEAD, clean) built as a raw 32 KB NROM PRG at
  `$8000-$FFFF`.
- Support/shim code at `$0800-$7FFF` in the same ROMBase bank (`$0F`).
- silky-gs HAL: NES task + GS task, 60 Hz VBL scheduler; NMI runs through
  `JSL` and returns `RTL`.
- `tileset.chr` converted by `nromBuild`; PPU writes are dispatched through the
  fixed shim table at `$7E00`.
- Credits loop completes, then `title_screen()` uploads the title nametable and
  fades in `palTitleBG`.

## Root cause of the earlier black screen

The C NMI handler only uploads `PAL_BUF` and OAM when `VRAMUPDATE != 0`
(`crt0_silky.s`). The patched `_ppu_waitnmi` only yielded; it never set
`VRAMUPDATE`, so `pal_all`/`pal_fade_in` changed the C shadow palette but the
PPU palette shadow stayed black. The renderer therefore drew the title tiles
with an all-black palette.

Fix: `_ppu_waitnmi` sets `VRAMUPDATE = 1` before `SHIM_YIELD`. The NMI handler
then uploads `PAL_BUF` every frame. That produced the visible title.

## Known limitations (next work)

1. **Title is currently wider than one nametable in the renderer.** The
   screenshot shows `ALTER` and `EGO` side by side because the renderer
   displays both horizontal nametables; the NES code toggles `scroll(0/256)`.
   The `EGO` half also has an attribute/tile approximation issue and is not yet
   a faithful match.
2. **No input yet.** `_pad_poll` returns 0, so the title cannot transition to
   gameplay. Audio is stubbed for the PoC.
3. **No gameplay verification.** This PoC proves the C PRG + PPU/VRAM +
   palette + renderer path reaches and draws the title, not the game.
4. Diagnostic border writes from the debugging phase are still present in a few
   startup files; they do not affect the title but should be removed before
   upstreaming.

## Reproduce

The tree these commands used (`C:\dev\alter-ego\build\silky`) was retired on 2026-11-01; the
surviving, verified recipe is [`iigs/prg-src/README.md`](../iigs/prg-src/README.md):

```powershell
cd C:\dev\alter-ego\iigs\prg-src
ld65 -C nes_silky.cfg -o prg.bin objects\crt0_silky.o objects\neslib_new.o `
  objects\game_fixed.o objects\audio_silky.o C:\dev\cc65\lib\nes.lib
copy prg.bin C:\dev\alter-ego\iigs\src\games\alterego\prg.bin
cd C:\dev\alter-ego\iigs\src\games\alterego
node build.js
```

Then package the resulting `AlterEgoGS` (in `iigs/build/`) as `AlterEgoGS.S16` into a bootable
2mg and boot it in GSplus.  The screenshot was captured with F10 in GSplus 1.38.

- Image: `iigs/build/AlterEgo.2mg` (the current bootable image; the PoC-era
  `build/AlterEgoGS-Title.2mg` was retired with `C:\dev\alter-ego` on 2026-11-01)
- Screenshot: the PoC PNG `alterego-iigs-title-poc.png` lived in that retired tree and was not
  kept; the title screen of `iigs/build/AlterEgo.2mg` is the current equivalent.