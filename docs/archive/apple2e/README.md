# Alter Ego

Adapted sources of homebrew NES game 'Alter Ego' (which is in turn an adaptation of the other famous ZX Spectrum title with the same name).

![Game Screen 1](https://cloud.githubusercontent.com/assets/822988/23153273/77f7d5fa-f7bc-11e6-8a69-ca14747b964b.png)

This hacked version of the game features secret cow level (otherwise missing in the original game)!

![Game Screen 3](https://cloud.githubusercontent.com/assets/822988/23159361/58a26984-f7d7-11e6-834e-e825930a78ec.png)

# How to run?

## Mac OS X

Preparations (do it once if you don't have ``cc65`` and related tools):

```
brew install cc65
```

Install ``fceux`` NES emulator, this is optional, but you need it if you want to play resultant ``chase.nes`` file:

```
brew install fceux
```

Compilation:

```
make all
```

Play resultant file:

```
make play
```

## Linux

Installation and compilation is identical to Mac OS X instructions above. Replace brew with packet manager that your OS supports and voila!

# Apple //e Port (ARCHIVED 2026-10-26)

> **Archived.** The //e DHGR route is no longer the mainline: its fixed palette
> and color-cell/fringing limitations make NES art a visible demake. The current
> target is **Apple IIgs / silky-gs**; see
> [docs/PORT-IIGS-SILKY-EVAL.md](docs/PORT-IIGS-SILKY-EVAL.md). The //e notes
> below are retained as historical and game-logic reference only.

A historical Apple //e (128K) port. Graphics use **DHGR** (real 16-colour
palette), music uses a **Mockingboard** (AY-3-8913). The deliverable was a
bootable DOS 3.3 disk image; this route is archived.

## Build (Windows)

Requires cc65 (`C:\dev\cc65`) and the pom2games kit (`C:\dev\pom2games`).

```
tools\build_a2.ps1     # generates assets, assembles, packs the DOS 3.3 disk
```

Output: `build\a2\ae2_game.dsk`. Boot in AppleWin:

```
C:\dev\applewin\x64\Release\AppleWin-x64.exe -d1 build\a2\ae2_game.dsk -model apple2ee -no-full-screen -aux ext80
```

(`-model apple2ee` = the *enhanced* //e — required so the 0x0D/0x5E/0x5F soft
switches latch 80COL/DHIRES; `-aux ext80` = the Extended 80-column aux card,
which keeps VF_DHIRES alive.) Verify the window title reads "Apple //e
(enhanced)" — "Apple //e (original)" silently decodes everything as plain-HGR.

## Historical //e status (archived)

- **DHGR engine verified working** (init / clear / solid fill / draw_screen all
  run correctly on AppleWin). `src/a2/dhgr.s`.
- **`dhgr_draw_screen` paints the title art** (ALTER EGO / PRESS START both
  appear; the earlier "renders only solid colour" observation came from a
  link-address bug in the demo binary, now fixed).
- **Open issue (decode path):** on the enhanced //e the glyph rows render as
  large solid orange/blue blocks in plain-HGR artifact RGB, while the
  background shows rainbow stripes. Within the DHGR lores palette the screen
  contains only black + white — AppleWin's RGB-card DHGR colour decode
  (`UpdateDHiResCellRGB`, nibble->colour rotation) is not producing the lores
  RGB the software model (`tools/_aw_model.py` -> `aw_decode_sim3.png`)
  produces. Diagnosis was in progress at archive time; see `AGENTS.md`.
- Music (Mockingboard / FamiTone2), level streaming, software sprites and the
  30fps render loop were never wired before archive.

See `docs/PORT-APPLE2-EVAL.md` (archived) for the historical //e evaluation and
`AGENTS.md` for the archived //e status. The current IIgs feasibility evaluation
is in [docs/PORT-IIGS-SILKY-EVAL.md](docs/PORT-IIGS-SILKY-EVAL.md).

# Apple IIgs Port (current)

The current port target is **Apple IIgs / silky-gs**. Alter Ego's NROM/static-CHR
structure fits silky, and SHR's 4096-colour CLUT gives a much closer NES palette
than //e DHGR (16 colours at once, 14–19 unique per screen in this game).

- Feasibility, blockers, risk table and phased plan:
  [docs/PORT-IIGS-SILKY-EVAL.md](docs/PORT-IIGS-SILKY-EVAL.md)
- Status: feasibility complete; implementation not started. First milestone is
  a title-screen PoC with the original HEAD `game.c` compiled into a silky
  `ROMBase` bank.

# Links

* [Programming NES games in C](http://shiru.untergrund.net/articles/programming_nes_games_in_c.htm)

