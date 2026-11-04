# Alter Ego on the web (jsnes)

Play the NES version in a browser: [`index.html`](index.html).  Pure client side, no server
required — double clicking the file works because the ROM is embedded as base64 by `build-rom.mjs`.

```
web/nes/
  index.html          page + styles
  app.js              loads the ROM, wires extra keys/buttons (jsnes does the rest)
  audio.js            our audio output (ScriptProcessor), replaces jsnes' AudioWorklet path
  vendor/jsnes.min.js jsnes 2.1.0, Apache-2.0 (see NOTICE.md)
  build-rom.mjs       compile src/ with cc65 and write build/alterego.nes + build/rom-base64.js
  nes-cc65-2.19.cfg   src/nes.cfg adjusted for the installed cc65 (see below)
  capture.mjs         headless run -> PNG captures (frame-by-frame inspection)
  test.mjs            smoke test: boot -> title -> Start -> Level 1, checked on pixels
  png.mjs             tiny PNG writer (no npm dependencies)
  build/              generated, gitignored
```

## Use

```powershell
cd web\nes
node build-rom.mjs        # compiles ../src with cc65/ca65/ld65 (needs cc65 2.19+)
node test.mjs             # PASS/FAIL + PNGs in build/shots/
```

`build-rom.mjs --from <any.nes>` stages a ROM instead of compiling one (the original v1.02 release,
for example).  Set `CC65_BIN` if cc65 is not at `C:\dev\cc65\bin` or on `PATH`.

Then open `index.html` (double-click works, or serve the directory with any static server for mobile
use) and **click the overlay** — that first click both starts the game and unlocks audio, as browsers
require.  Keys: arrows, `X` = A and `Z` = B (exchange), `Enter`/`Space` = START, `Ctrl` = SELECT, `R`
reset, `F` fullscreen; a numeric keypad also gives A/B/START/SELECT on `7`/`9`/`1`/`3`.  The same pad
is on screen under the bar (`← ↑ ↓ → B A SELECT START`) for touch and mouse, and clicking an on-screen
button is the quickest way to tell a keyboard problem from a game rule.  The bar has Reset / Pause /
Mute / Volume / Fullscreen / Load another .nes, and any `.nes` can be dropped on the page.  Cold boot
starts with the original NES credits screen (English text, as on the real cartridge); Space skips it.

The header has the large **ALTER EGO** title on the left and, at its right edge — the header is exactly
the stage's width, so the links stop at the emulator's right border — the Apple II VERA port (Apple2TS,
our own Pages build at <https://anomixer.github.io/apple2ts/> — upstream `apple2ts.com` has a broken VERA
display), the Apple IIgs port (a2gsemu-ia) and the GitHub mark for
<https://github.com/anomixer/alter-ego>.

## Published site (GitHub Pages)

The player is deployed: <https://anomixer.github.io/alter-ego/nes/index.html>.  The site root,
<https://anomixer.github.io/alter-ego/>, is [`web/index.html`](../index.html) — one card per target
(NES, Apple IIgs, Apple //e + VERA) — and the player is `nes/index.html` under it.

[`.github/workflows/deploy-web.yml`](../../.github/workflows/deploy-web.yml) runs on every push that
touches `src/` or `web/`: it installs cc65, runs `build-rom.mjs`, then `test.mjs` (so a ROM that does
not reach the title fails the deploy instead of being published), assembles `web/_site` with
[`web/build-site.mjs`](../build-site.mjs) and uploads that directory as the Pages artifact.  The
repository must have Settings → Pages → Source set to **GitHub Actions**; nothing else is configured,
and no branch is served.

`build-site.mjs` publishes only the page files plus the generated `build/alterego.nes` and
`build/rom-base64.js`; it also refuses to assemble a site whose HTML points at a missing local file.
`web/_site` is gitignored.

The root page's heading is the game's own word mark, not text: `web/assets/alter-ego-logo.png`
(206×39, committed) is cut from the NES title screen by [`make-logo.mjs`](make-logo.mjs).  The title
draws each word twice — a bright copy and a dimmer one one word-height away (ALTER's under the letters,
EGO's above them); the page keeps one copy per word and drops the other, which is the "reflection" the
user did not want.  ALTER comes from the background copy and EGO from the sprite copy, each recoloured
by shade rank onto the other word's ramp (so ALTER is orange/amber and EGO blue), the 1-4 px stars are
dropped by component size, and black becomes transparent so the letters sit on the page's dark
background.  The words keep the title's own columns but are moved up to a common top row, so the mark
is a single line (206×39) with the title's 17 px gap between ALTER and EGO.  Re-run
`node web/nes/make-logo.mjs` (`--report` prints what it kept and dropped) if the
title art ever changes; `png.mjs` has `writePngRgba` for the alpha.

The cc65 package on Linux keeps `nes.lib` outside `bin/` (`/usr/share/cc65/lib/nes.lib`), so
`build-rom.mjs` accepts `CC65_LIB` and otherwise tries the usual Linux/macOS locations; the workflow
passes it explicitly.  A CI checkout therefore builds the same ROM as a local one:

```
ROM 40,976 bytes (32 KB PRG + 8 KB CHR, mapper 0), title at 252 frames, Level 1 92 frames after Start
```

## Sound: why app.js drives audio itself

jsnes' `Browser` class plays through an `AudioWorklet` module that it builds as a `blob:` URL.  When
the page is opened from `file://`, Chrome never loads that module (the promise does not even settle,
and nothing is reported), so the game looked and played fine but was completely silent.  `audio.js`
takes over: `nes.opts.onAudioSample` feeds a `ScriptProcessorNode` ring buffer, linear-resampled from
jsnes' 44.1 kHz to the `AudioContext` rate (48 kHz here), and `Browser.start`'s speaker call is
no-opped so there is no second (silent) path.  This works from `file://` and from a static server
alike; the status line shows the measured rate (`Sound: 90% (44100 Hz→48000 Hz)`), and the
Mute/Volume controls drive the gain node.  All page text is English.

## Layout, Reset and fullscreen

Three things jsnes' own `Browser` gets wrong for this page, and how they are handled:

- The canvas inherits `fitInParent()`'s inline pixel size, and the page's flex column used to squeeze
  `#stage` below its 256:240 aspect, so the picture got a black band on the right.  `#stage` now has
  `flex: none`, and `#screen canvas` is forced to `100%` so the canvas always fills the 256:240 box.
- `F` / Fullscreen asks the stage for fullscreen and centres a 256:240 box inside the viewport, so the
  picture really fills the screen (letterboxed only when the monitor is not 4:3).
- Reset does *not* call `nes.reset()`: that rebuilds the cpu/ppu/papu but not the mapper, which left the
  game wedged.  `app.js` boots the ROM again instead, keeping the bytes from the last load.

Exchange is bound to `X` (A) and `Z` (B), as the game expects.  The ROM reads `PAD_A|PAD_B` in the
`player_dir == DIR_NONE` branch (`game.c` L1206 -> L1234), so a press that lands while a direction key
is held can be ignored -- stop, then press.  It is also ignored while the swap animation runs.

## Input: mapped from `event.code`, not jsnes' key table

jsnes' `Browser` looks keys up in a table keyed by the deprecated `event.keyCode`, and it loads that
table from `localStorage` first.  Two things break as a result:

- With a Chinese IME, typing `X` or `Z` starts a composition, so both arrive as **keyCode 229** — the
  arrows and Enter still work, which makes it look like only the exchange buttons are dead.
- Any `keys` entry another jsnes page saved in `localStorage` silently remaps the pad.

`app.js` therefore maps `event.code` (`KeyX`, `KeyZ`, `ArrowUp`, `Enter`, `Space`, `Ctrl`, …) straight
onto the pad and clears jsnes' table in `boot()`, so the same press is not applied twice.  Space is
mapped to START as well, which is what the footer offers for skipping the credits.

There is a second, nastier IME failure mode: the **keydown** arrives normally (`KeyX`), but the
**keyup** belongs to the composition and carries no usable code (`key: "Process"`, `keyCode 229`).
The page then kept thinking A was still down, jsnes reported A pressed on every frame, and the ROM --
which only accepts an exchange when A/B are released after the last one -- refused every later press
with the exchange counter untouched.  Mashing X on the credits screen before the level started was
enough to get there, and from then on nothing (keyboard or the on-screen buttons) could exchange.
Action buttons (A/B/SELECT/START) are now taps: they release themselves 400 ms after going down if the
keyup never arrives, an IME-shaped keyup or `compositionend` releases them immediately, and clicking an
on-screen button releases it before pressing.  Direction keys are still hold-to-walk.

Exchanges are a resource: each level hands out a fixed number (level 1 gives **two**, shown as the
second HUD counter).  Once it reaches zero the ROM plays the "cannot exchange" sound and ignores the
button until the level is cleared -- so a "dead" `X` with the counter at zero is the game, not the
page.

For diagnosis there is no on-screen text; the same facts are on `window.__ae` in the console:
`lastKey` (the raw `code` / `key` / `keyCode` of the last press), `lastPad`, `held`, and `hud`
(`{ restart, exchange }`, read from sprite 58/59, tiles `0xe5+n`).  `hud.exchange` is the number a
press spends; if it drops, the press worked.

## The ROM is built from source, not committed

The repository root now mirrors <https://github.com/avshabanov/alter-ego> (upstream), so `make all`
is a working NES build again — `src/game.c` is upstream's native neslib C, not the Apple //e
variant that the earlier layout kept there.  `build-rom.mjs` runs the same five steps as the root
`Makefile` (`cc65`, two `ca65` objects, the generated `game.s` -> `game.o`, `ld65`) and embeds the
result as base64, so the page always plays a ROM produced from this tree and no binary is shipped.

Two adjustments are needed for the toolchain installed here (cc65 2.19):

- `src/nes.cfg` uses the pre-2.19 `SYMBOLS` form (`__STACKSIZE__ = $0500;`), which `ld65` rejects with
  “Symbol attribute expected”; `nes-cc65-2.19.cfg` is the same file with
  `__STACKSIZE__: type = weak, value = $0500;` and an `ONCE` segment (the installed library has one).
  Keep it in sync with `src/nes.cfg` if upstream changes.
- The checked-in `src/nes.lib` is the historical cc65 library and `ld65` V2.19 rejects it
  (“Wrong data version”), so the `nes.lib` installed next to cc65 is linked instead.

The resulting ROM is 40,976 bytes (32 KB PRG + 8 KB CHR, mapper 0), the same shape as the original
`Alter_Ego.nes`; the bytes differ because a newer cc65/lib built it.

## Smoke test

`node test.mjs` boots the ROM headlessly (jsnes `NES` class), skips the cold-boot credits screen
(~240 frames), waits for the title signature, presses Start, waits for Level 1, and checks pixels
(title: black sky + blue/orange logo; Level 1: white frame + blue playfield).
Measured on the source-built ROM: title at 252 frames, Level 1 92 frames after the Start press,
exit 0.  Captures land in `build/shots/title.png` and `build/shots/level1.png`.
