# Filed upstream — pre-built/embedded compiled sprites

- **Filed:** 2026-11-03
- **Where:** <https://github.com/lscharen/iigs-game-engine/issues/29> (open)
- **Title:** Pre-built/embedded compiled sprites: data point from a CHR-ROM port
- **Why it is here:** record of what was filed, so the port's log and the issue cannot drift apart.

The body below is the text of issue 29, kept verbatim.

---

Context: I maintain an Apple IIgs port of Alter Ego -- Denis Gratchev's ZX Spectrum game,
NES version by Shiru (music by Kulor, hack by Alex Shabanov) -- running on a v0.0.2-era
snapshot of silky-gs (0c341d2). The game is NROM with a fixed 8 KB CHR-ROM
(`HAS_CHR_RAM equ 0`), i.e. exactly the "non CHR-RAM game" case you mentioned, so this
change would apply to us directly.

For context on where we are: we're not CPU-starved -- at a 2.8MHz cap (~2.55 MHz
effective in GSplus) the game holds ~60 logic fps. What we'd want out of pre-built
sprites is startup time and headroom, not playability.

Port sources, if useful: https://github.com/anomixer/alter-ego
- engine-relevant files are under `iigs/`, per-game code is `iigs/src/games/alterego/`
- `iigs/src/game/` is build scratch, not a source of truth
- `iigs/AGENTS.md` and `iigs/CLAUDE.md` describe the layout

What we observe in v0.0.2: the sprite compiler is already lazy and cached per (tile,
palette, flip), dispatched through `SPR_COMP_TBL` with no separate dispatch code, so in
steady state a sprite costs roughly the table lookup plus the `jml` into the compiled
variant. The two places pre-building would show up for us:
1. startup -- the first screens compile their tiles one at a time, and startup is
   user-visible because the game boots from a ProDOS disk image;
2. later cache misses -- we do see screens recompile after a palette switch.

Questions, since the answers decide whether we could adopt it as-is:
1. Scope: whole-game at build time, or per screen (the sprite set of that screen)?
2. CHR layout: does it assume a fixed one? NROM uploads the 8 KB once and never changes
   it, so a whole-game pre-build would be valid for us; CHR-RAM games would need a path
   back to the runtime compiler.
3. Fallback: does the runtime compiler stay for cache misses, or does the pre-built path
   replace it entirely?

No schedule expectation -- posting this so the data point is on record rather than to ask
for one.
