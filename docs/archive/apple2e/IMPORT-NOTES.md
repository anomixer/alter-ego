# Archived: the Apple //e working tree (`C:\dev\alter-ego`)

On 2026-11-01 the upstream / Apple //e working tree was removed from the machine.  This directory
keeps what was worth keeping from it; the rest is gone on purpose.

## What is here

| Path | What it was |
| --- | --- |
| `AGENTS.md`, `README.md` | the //e-era working log and README as they stood on 2026-11-01 (the //e route was already marked ARCHIVED on 2026-10-26) |
| `src-game.c` | the **uncommitted** //e rewrite of `src/game.c` (1710 lines against the 1606 committed lines) — the only copy that existed |
| `tools/*.py` | the //e investigation tooling: `a2_emu.py` (the only working observation channel), `a2_art.py` / `a2_assets.py` (DHGR art), `dos33_pack.py`, the `_aw_model.py` / `_verify_dhgr.py` decode checks, ~110 scripts in total |
| `tools/*.ps1` | the AppleWin / `a2run` automation harness (`aw*`) and the //e build script `build_a2.ps1` |

`docs/PORT-APPLE2-EVAL.md`, `docs/PORT-IIGS-SILKY-EVAL.md` and `docs/PORT-IIGS-TITLE-POC.md` were
moved up into `docs/` rather than archived here, and the `build/silky` PRG staging tree became
`iigs/prg-src/` (which reproduces the shipped `prg.bin` byte for byte — see its README).

## What was not kept

- `tools/a2run/` (350 MB): third-party Apple II emulator sources plus build output; re-downloadable.
- `build/` (219 MB): //e build outputs, screenshots, level payloads and the throw-away `build/silky`
  experiment variants (`game_menu*.o`, `prg_*.bin`, …).  Only the files needed to rebuild the PRG
  survive, in `iigs/prg-src/`.
- `_a2ref/`, `Alter_Ego.nes`, `config.kegs`, `copydata.o`, `zerobss.o`: reference copies and stray
  build leftovers.
- Two local-only git commits on its `test/gs` branch (`114d0b6` "Add Apple IIgs silky-gs port
  snapshot under iigs/", `612009d` "Record IIgs push status in work log"); the IIgs port itself lives
  in `iigs/` here, with all later fixes, so nothing executable was lost.
