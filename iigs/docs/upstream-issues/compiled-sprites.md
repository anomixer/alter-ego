# Filed upstream — pre-built/embedded compiled sprites

- **Filed:** 2026-11-03, refiled 2026-11-04
- **Where:** <https://github.com/lscharen/silky-gs/issues/46> (open)
- **Title:** Pre-built/embedded compiled sprites: data point from a CHR-ROM port (Alter Ego)
- **Why it is here:** record of what was filed, so the port's log and the issue cannot drift apart.

The first filing went to the wrong repository — `iigs-game-engine` issue 29, which lscharen closed as
completed with "This issue was opened in the wrong repository. Items related to the Silky-GS NES
runtime should be opened in the `silky-gs` repository." (`#29` also has a comment pointing at the
refile). The runtime is what this request targets, so the issue now lives in `silky-gs`.

The body below is the text of issue 46, kept verbatim.

---
Context: I maintain an Apple IIgs port of Alter Ego (Denis Gratchev's ZX Spectrum game, NES version
by Shiru; music by Kulor, hack by Alex Shabanov) running on a v0.0.2-era snapshot of silky-gs
(`0c341d2`). The game is NROM with a fixed 8 KB CHR-ROM (`HAS_CHR_RAM equ 0`), i.e. exactly the
non CHR-RAM case, so a pre-built/embedded sprite path would apply to us directly.

Where we are: we are not CPU-starved — at a 2.8 MHz cap (~2.55 MHz effective in GSplus) the game
holds ~60 logic fps and a full render fits in one VBL. What we would want out of pre-built sprites
is startup time and headroom, not playability.

Port sources, if useful: <https://github.com/anomixer/alter-ego>
- engine-relevant files are under `iigs/`, per-game code is `iigs/src/games/alterego/`
- `iigs/src/game/` is build scratch, not a source of truth
- `iigs/AGENTS.md` and `iigs/CLAUDE.md` describe the layout

What we observe in v0.0.2: the sprite compiler is already lazy and cached per (tile, palette,
flip), dispatched through `SPR_COMP_TBL` with no separate dispatch code, so in steady state a
sprite costs roughly the table lookup plus the `jml` into the compiled variant. The two places
pre-building would show up for us:

1. **Startup** — the first screens compile their tiles one at a time, and startup is user-visible
   because the game boots from a ProDOS disk image (an 800 KiB GS/OS boot disk that launches the
   game directly as `/SYSTEM/START`, so there is no Finder and no desktop).
2. **Later cache misses** — we do see screens recompile after a palette switch.

Questions, since the answers decide whether we could adopt it as-is:

1. Scope: whole-game at build time, or per screen (the sprite set of that screen)?
2. CHR layout: does it assume a fixed one? NROM uploads its 8 KB once and never changes it, so a
   whole-game pre-build would be valid for us; CHR-RAM games would need a path back to the runtime
   compiler.
3. Fallback: does the runtime compiler stay for cache misses, or does the pre-built path replace it
   entirely?

No schedule expectation — posting this so the data point is on record rather than to ask for one.

(First filed in `iigs-game-engine` as #29; it was closed there as being in the wrong repository.)
