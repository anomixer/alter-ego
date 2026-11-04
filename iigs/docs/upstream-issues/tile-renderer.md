# Draft (not filed) — question about the experimental tile renderer

- **Status:** draft, deliberately **not** filed.  Upstream (2026-11-03) says the renderer is "not
  close to ready"; the only thing this port needs from it is whether it changes the PPU shadow /
  queue ABI, because this tree is a v0.0.2 snapshot with its own in-bank `$7E00` shim table.
- **File it when:** upstream announces the renderer, or when a frame-budget problem makes adoption
  worth evaluating.
- **Where it would go:** <https://github.com/lscharen/silky-gs/issues> (new issue).  The runtime lives
  in `silky-gs`; `iigs-game-engine` is the wrong repository for runtime questions (2026-11-04, after
  the compiled-sprites request was closed there for that reason and refiled as `silky-gs` issue 46).

## Title

```
Tile renderer: what does it replace, and does it change the PPU shadow ABI?
```

## Body

```
Two questions so I can judge whether a v0.0.2-era fork can adopt it incrementally or
needs a porting pass:

1. Scope: does it replace the full-render blitter path (BlitterLite / TemplateLite banks /
   PEISlammer), the dirty quad grid, or both?
2. ABI: does it change the PPU shadow layout, the queue interface, or the register write
   shims? My port is a v0.0.2-era snapshot with a local in-bank shim table at $7E00 that
   ends in `jsl` into the engine bank, so anything on the shadow-register side costs me a
   porting pass rather than a drop-in.

If it helps I can send a frame-time split of full render vs dirty render from the port,
though our load (a single non-scrolling screen with dirty rendering) may not be
representative.
```

## Context for when it is filed

- This port's per-frame shim traffic is small (PPUCTRL/PPUMASK, 2x PPUSCROLL, 1x OAM DMA, and
  `$2006`/`$2007` only during screen loads), so the shim-dispatch half of upstream's optimisations
  is worth <0.5% of a 46,666-cycle frame here.
- What actually costs this port time is a full render (screen changes: title, credits, level loads);
  the dirty grid already keeps steady-state gameplay at ~30 fps on a 2.8 MHz machine.
