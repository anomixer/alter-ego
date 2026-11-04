# AGENTS.md — Alter Ego / Apple IIgs work log

This file is the working log and hand-off for the **Apple IIgs (silky-gs)** port. It supersedes the
archived `//e` notes in `vera/docs/archive/apple2e/`. Dates are Asia/Taipei.

## 2026-11-04i — the mark: ALTER orange, EGO blue, one copy of each word

「1. 右邊EGO變黃了?  原來不是偏藍色嗎? 2. ALTER只要上面的這5個英文字就好, 不用倒影, EGO也是一樣」,
then 「ALTER原本是偏橘黃色, 結果變藍色 (看來上一輪你把ALTER和EGO的顏色對掉了XD)」.  Both are right,
and both come from the same fact: the title draws each word **twice**, in two different ramps.

### What the title screen actually draws

Measured in jsnes at frame 420, and identical at frames 250-3000 (so the title art is static, there is
no colour cycling to chase):

| what | where | shades | px |
|---|---|---|---|
| ALTER, bright copy | x 25..142, y 56..94 | `0,25,188` / `0,180,247` / `136,237,248` | 1,745 |
| ALTER, dim copy | x 9..165, y 96..118 | `255,64,0` / `180,0,0` / `255,171,60` / `255,242,190` | 1,610 |
| EGO, bright copy | x 160..230, y 96..134 | `255,64,0` / `255,171,60` / `255,242,190` | 1,389 |
| EGO, dim copy | x 161..230, y 72..94 | `0,0,95` / `0,25,188` / `71,109,255` | 849 |

- Every attribute bit on the title's background tiles is 0, so all of them use BG group 0 =
  `{0x0f, 0x01, 0x11, 0x21}` (`palTitleBG`, `src/palettes.h`) — the **blue** ramp.  So the background
  letters are blue and the orange ones are the sprite layer: on the NES, ALTER is blue and EGO orange,
  and each word's dim copy is the 倒影 (dimmer, one word-height away: under ALTER, above EGO).
- The IIgs port's title shows the same art with the two ramps exchanged — ALTER letters `255,0,0` /
  `255,170,68` / `255,255,119` (the orange ramp), EGO letters `119,187,255` — measured on
  `docs/screenshots/shot_title_current.png`.  That is the look the user remembers; it is a
  title-screen palette mismatch on the port, not what the NES ROM does, and it is **not** touched here.

### The recolour

`web/nes/make-logo.mjs` now keeps **one copy per word** — ALTER from the background copy, EGO from the
sprite copy — and drops the other copy plus the 1-4 px stars (components under 16 px).  Each word's
shades are mapped by rank onto the other word's ramp, so ALTER comes out `255,64,0` / `255,171,60` /
`255,242,190` and EGO `0,25,188` / `0,180,247` / `136,237,248`.  Placement is untouched, so the two
words keep their title-screen geometry; the crop was **206×79** (one column narrower, ALTER's bbox) —
see the follow-up below for the single line.

### Verified

- `node web/nes/make-logo.mjs --report`: ALTER 1,644 px kept (101 px of stars dropped), bbox
  `x 25..142 y 56..94`; EGO 1,353 px kept (36 dropped), bbox `x 160..230 y 96..134`; asset 206×79,
  2,997 opaque px, 1,234 B, SHA256 `614c0910106c21783c9943fca1a048c0ebd0f9adb88f615ebdc574d9d6d105e1`.
- `web/index.html` sizes it `min(412px, 84vw)` = 2× 206 with `width`/`height` 206×79.
- Deploy run `41805598074` (`de59715`): build and deploy **success**, every step green.
- Live: `/index.html` 200 (3,689 B) carrying the logo reference and the `min(412px` rule; the asset
  200, 1,234 B, byte-identical to the committed file (same hash above); the live screenshot at
  1100×940 is byte-identical to the local one — ALTER orange/amber, EGO blue, nothing under or over
  either word.

### Follow-up — one line (同一行)

「把logo放在同一行吧! 不用左上右下」.  The mark is now a single line: `make-logo.mjs` moves every word
up to the block's top row (both are five tile rows tall, so they share a baseline as well) and leaves
the columns alone, so the 17 px between the words is still the title's own spacing.  EGO shifts by
dy −40; the crop goes **206×79 → 206×39** with the same 2,997 pixels, 1,135 B, SHA256
`d534513981fd0394ccb8fd060b20967fab45cf7204da406726791ea4e0c5cf48`.  `web/index.html` carries
206×39 (and `h1` margin 12 px).

Deploy run `41810062823` (`2516b9e`): success; live `/index.html` 200 (3,689 B) with `height="39"`,
the asset 200 / 1,135 B and byte-identical to the committed file, and the live screenshot at 1100×900
byte-identical to the local one — ALTER left in orange, EGO right in blue, one line.

The docs commit after it (`19122bc`) touched `web/nes/README.md`, i.e. a path the workflow's `paths`
filter covers (`web/**`), yet GitHub created **no** run for that push — a transient, not a filter
problem: dispatching the same workflow by hand worked at once.  So that head was deployed with
`workflow_dispatch`, run `41811270854` (`19122bc`), **success** with every step green, and the live
page and asset re-checked afterwards: still 1,135 B / `d5345139…`, page 200 (3,689 B) with
`height="39"` / `width="206"`.

### Trap — one `Set-Content` rewrite ate five characters

`web/index.html` was rewritten through PowerShell's `Set-Content` when the mark was recoloured
(`de59715`), and that round-trip turned every character it could not map into a literal `??`: the
`<title>`'s em dash, the subtitle's em dash, and all three `👉` in the card headings.  Nothing failed
— the page just rendered `?? PLAY HERE`, which the 1100×900 screenshots show.  Restored in the next
commit: the file is UTF-8 again (3,699 B, `—` / `👉` / `·`), and `git diff de59715 HEAD -- web/index.html`
is exactly those five lines.

Reading the tree back with Windows PowerShell 5.1 makes this look worse than it is: `Get-Content`
decodes UTF-8 as ANSI, so *every* `—`, `←`, `→`, `…` prints as `?` and the file looks riddled with
`??`.  Check encoding with `node -e "readFileSync(...,'utf8')"` (or the `edit` tool), never with a
PowerShell read-modify-write.

Fixed in `b8efb1f`; deploy run `41812352855` (that push, so the earlier "no run" really was a one-off)
built and deployed **success**, and the live page is now 3,699 B with zero `??`: `height="39"` /
`width="206"`, both em dashes and three `👉`, the asset 200 / 1,135 B / `d5345139…`, and the live
1100×900 screenshot byte-identical to the local one.

### The //e VERA player moved to the Pages build of Apple2TS

「先幫我 iivera 版本 改成 <https://anomixer.github.io/apple2ts/...> (上游把iivera display修壞了 orz)」.
All three links that open the Apple //e + VERA port now use **`https://anomixer.github.io/apple2ts/`**
with the same `?slot2=vera&tab=vera#<raw hdv>` tail, instead of `apple2ts.com`: `README.md` (the PLAY
HERE table), `web/index.html` (the card) and `web/nes/index.html` (the header pill).

Checked that the new target actually plays, not only that it answers:

- the Pages build is Apple2TS itself (2,227 B page, `assets/index-CLRNaERo.js`, which still parses
  `slot2` / `tab=` / `location.hash`), and `apple2ts.com` was not touched;
- the raw `.hdv` is 819,200 B and byte-identical to the committed `vera/build/alter-ego-vera.hdv`;
- the exact link, driven in headless Chrome over CDP in **real** time (not virtual time), boots the disk
  into slot 7 drive 1 and the **VERA display** pane shows the port's title menu — ALTER EGO with
  `START GAME` / `START LEVEL 01` / `MUSIC ON` / `SOUND ON`, i.e. the display that upstream broke works
  here. Capture: `web/nes/build/shots/a2ts-01-boot.png` (scratch, gitignored).

Windows note: on this machine `Invoke-WebRequest` and Node's `fetch` against `anomixer.github.io`
sometimes fail with `ERR_CONNECTION_RESET` / `ECONNRESET` while `curl.exe` and Chrome get 200 every
time — a local network quirk, not the host rejecting the request.

Deployed in `ee49fac` (deploy run `41837661445`), **success**; live `/index.html` (3,714 B) and
`/nes/index.html` (8,612 B) each carry exactly one `anomixer.github.io/apple2ts/` link and no trace of
`apple2ts.com`.

### Files touched

- `web/nes/make-logo.mjs` (word-by-word extraction, ramp mapping, `--report`), `web/assets/alter-ego-logo.png`,
  `web/index.html` (206/412 px), `web/nes/README.md` (the paragraph now describes the two copies),
  the 2026-11-04h claim about "no reflection" corrected, this entry.

## 2026-11-04h — the landing page's heading is the game's own title mark

「就 github pages 首頁 ALTER EGO, 看能否用 NES畫面那個 ALTER EGO logo (不用倒影)」 — so the Pages root
(`web/index.html`) no longer sets the title in Segoe UI; it shows the mark from the NES title screen.

### Where the mark comes from — cut out of a real frame, not redrawn

`web/nes/make-logo.mjs` boots `build/alterego.nes` in jsnes, runs to frame 420 (the title), and keeps
only what is big enough to be a letter:

- the title's stars are 1-4 px components, so 4-neighbour components under 16 px are dropped
  (243 px of stars in that frame); the letters are 200+ px each.
- the mark is rows **56..134** and columns **24..230** → a **207×79** crop; "PRESS START" (rows 178..190)
  and the credits text are outside the band `40..170`, so neither can leak in.
- black becomes transparent (`writePngRgba`, colour type 6, added to `png.mjs`), so the letters sit on
  the page's `#0b0b10` instead of on a black rectangle: 5,210 opaque px, 11,143 transparent.

**There *is* a second copy of each word, and that is what the user calls 倒影.**  The first version of
this entry claimed the title had nothing to leave out, which was wrong: each word is drawn twice, a
bright copy and a dimmer copy one word-height away (under ALTER's letters, above EGO's), plus the
scattered stars.  The correction and the recolour are in 2026-11-04i below.

### On the page

`h1` holds the image at `min(414px, 84vw)` — 414 is exactly 2× the 207 px art, so with
`image-rendering: pixelated` every source pixel gets the same size on screen (and it is 4× at DPR 2);
`width`/`height` attributes carry the 207:79 ratio so nothing shifts while it loads.  `build-site.mjs`
copies `assets/` too, and its local-reference check covers the new `src`.

### Verified

- Local: `node web/nes/make-logo.mjs` → `frame 420: 366 components, kept 123 (dropped 243 px of stars)`,
  box `x 24..230, y 56..134`, 1,668 B PNG; screenshot of the assembled site at 1100×940 shows the mark
  above the three cards, no black box, no stars.
- Deploy run `41801436511` (`04a0df3`): build and deploy **success**, every step green.
- Live: `/index.html` 200 (3,699 B) with the `assets/alter-ego-logo.png` reference, the asset 200
  `image/png` 1,668 B and byte-identical to the committed file
  (`316db4838d6cb0fd35ff406b4a9a58aa6438e7e162a12fd19dd12a57f9ed731f`); the live screenshot is
  pixel-identical to the local one.

### Trap

Windows locks the cwd, so a `python -m http.server` started **inside** `web/_site` makes
`build-site.mjs`'s `rmSync` fail with `EPERM`; serve with `--directory` from another directory (or stop
the server) before rebuilding.

### Files touched

- `web/index.html` (h1 → image, `h1 img` CSS), `web/assets/alter-ego-logo.png` (new, committed),
  `web/nes/make-logo.mjs` (new), `web/nes/png.mjs` (`writePngRgba`), `web/build-site.mjs` (`assets/` in
  the manifest), `web/nes/README.md` (how the mark is made), this entry.

## 2026-11-04g — player header: bigger title, port links at the top right

Two changes to `web/nes/index.html`, both from the user's read of the deployed page:

- **The title was too small** (18 px, centred).  `h1` is now `clamp(26px, 4.2vw, 36px)` — 36 px at the
  768 px stage width — with the left-aligned brand block plus the "jsnes 2.1.0" subtitle.
- **The header had no way back to the other ports.**  It is now a flex row exactly as wide as the
  emulator stage (`min(768px, 100%)`), with, at its right edge in this order: the **Apple II VERA** port
  (Apple2TS, raw `vera/build/alter-ego-vera.hdv`), the **Apple IIgs** port (a2gsemu-ia,
  `?game=<repo>`), and a **GitHub mark** linking <https://github.com/anomixer/alter-ego>.  The links
  are pill-shaped, 30 px tall; the header is the stage's width, so nothing runs out past the emulator's
  right border, and it wraps below the title when the window is narrow.

### Verified

- Measured in headless Chrome (1000×1000) on **both** the local site and the deployed one: title
  `36px`, stage spans `107..877`, the nav spans `629..876` and `fitsStage` is true — the GitHub icon
  ends 1 px inside the stage's right border.
- The deployed page still plays: after the click the status line reads
  `ROM build/alterego.nes (embedded) · 40,976 bytes · Sound: 90% (44100 Hz→48000 Hz)`, the canvas is
  256×240, and Space reaches the title (non-black **5459**, the `test.mjs` signature).
- The three link targets answer 200: a2gsemu-ia, Apple2TS, and the raw VERA `.hdv` behind it (plus the
  repository page).
- Deploy run `41798982225` (`head 2a556a5`): build and deploy **success**; the live
  `/nes/index.html` serves 8,597 bytes with the new CSS and all three links.

### Files touched

- `web/nes/index.html` — header markup/CSS (`header`, `.brand`, `.ports`, `h1` clamp, GitHub SVG); the
  footer now says the ROM is compiled "when this site is built" instead of "locally".
- `web/nes/README.md` — the header and its three links described; this entry.

## 2026-11-04f — Play in a browser: PLAY HERE links and the NES player on GitHub Pages

The root `README.md` now has the three "PLAY HERE" links the user asked for (the freegemas layout):
the jsnes page at <https://anomixer.github.io/alter-ego/nes/index.html>, the IIgs port through
a2gsemu-ia (`?game=<repo url>`, so it boots the released `AlterEgo.2mg`), and the VERA port through
Apple2TS (raw `vera/build/alter-ego-vera.hdv`).  The table sits right under the repository table, and
`## Play the NES original in a browser` repeats the NES link.

### The NES page is deployed, not just local

`web/nes/` used to be a local page only.  It is now published, on the URL the user named:

| URL | What it is |
|---|---|
| <https://anomixer.github.io/alter-ego/> | `web/index.html`, one card per target |
| <https://anomixer.github.io/alter-ego/nes/index.html> | the player |

- [`.github/workflows/deploy-web.yml`](../../.github/workflows/deploy-web.yml) — runs on a push that
  touches `src/**`, `web/**` or itself, and on `workflow_dispatch`.  It installs cc65 from apt, runs
  `web/nes/build-rom.mjs` (compiles `src/`; **no ROM is committed**), then `web/nes/test.mjs`, which
  pixel-checks title and Level 1 — so a ROM that does not reach the title fails the deploy instead of
  being published — assembles `web/_site` and deploys it with `actions/deploy-pages@v4`.
- `web/build-site.mjs` — assembles `web/_site` from the tracked page files plus the generated
  `build/alterego.nes` and `build/rom-base64.js`, and fails when an HTML local reference is missing.
  `web/_site` is gitignored (`web/.gitignore`).
- `web/index.html` — the Pages root.
- `web/nes/build-rom.mjs` — gained `CC65_LIB` and the usual Linux/macOS library locations: the cc65
  package keeps `nes.lib` outside `bin/` (`/usr/share/cc65/lib/nes.lib`), and the workflow names it
  with `find /usr -name nes.lib -path '*cc65*'`.  Windows behaviour is unchanged (it still links
  `C:\dev\cc65\lib\nes.lib`).

### Verified end to end

- Local: `node web/nes/build-rom.mjs` → 40,976 B (32 KB PRG + 8 KB CHR, mapper 0, SHA256
  `D05E814E…`); `node web/nes/test.mjs` → **PASS** (title 252 frames, Level 1 92); `node
  web/build-site.mjs` → 8 files / 257,023 B.
- GitHub Actions run `41796726854` (`2026-11-04T08:04:35Z`): build job and deploy job both
  **success**, every step green, first try.
- Live: `/`, `/nes/index.html`, `/nes/build/rom-base64.js`, `/nes/build/alterego.nes` and
  `/nes/vendor/jsnes.min.js` all answer **200** with the expected sizes.
- Live, in Chrome (headless, real time, clicked the page): the status line reads
  `ROM build/alterego.nes (embedded) · 40,976 bytes · Sound: 90% (44100 Hz→48000 Hz)`, the canvas is
  256×240, and Space lands on the title with **non-black 5459** — the exact signature `test.mjs`
  asserts, so the published page plays the published ROM.
- Pages was **already enabled** with `build_type = "workflow"` (the `POST /pages` answered 409), so
  no repository setting had to change; the docs still say Settings → Pages → Source: GitHub Actions in
  case it is ever turned off.

### Traps

- **The CI build is not byte-identical to a local one.**  The deployed `alterego.nes` hashes
  `E75209A0…`, the local cc65 build `D05E814E…`; same 40,976 bytes and same shape, both pass the same
  pixel test.  apt's cc65 differs slightly from `C:\dev\cc65` (2.19 as well), so the ROM hash is not
  an identity test — the `test.mjs` signatures are.
- **A click before `app.js` is ready is lost.**  The overlay's handler is attached at the end of
  `app.js`; the status line still says `Loading…` until then.  A probe that clicks as soon as `#status`
  exists does nothing and reports "no canvas" — wait for the status text to leave `Loading…`.
- **No ROM in git.**  `Alter_Ego.nes` (the original v1.02 binary at the root) stays untracked;
  `web/nes/build/` is generated.  The site is built from source on every deploy.

### Files touched

- `.github/workflows/deploy-web.yml`, `web/build-site.mjs`, `web/index.html`, `web/.gitignore` (new).
- `web/nes/build-rom.mjs` (`CC65_LIB` / Linux library paths), `web/nes/README.md` (deployment section,
  library note), `README.md` (PLAY HERE table, workflow in the pages table and the documentation
  group), `iigs/README.md` (a2gsemu-ia link in the release section), this entry.

## 2026-11-04e — first release: tag `iigs-v0.0.2`

The port is published.  Tag **`iigs-v0.0.2`** on the 2026-11-04 commit, GitHub release
<https://github.com/anomixer/alter-ego/releases/tag/iigs-v0.0.2>, two assets — the tracked files from
`iigs/build/`, byte for byte, so nothing was repacked for the release:

| Asset | Bytes | SHA256 | Disk |
|---|---|---|---|
| `AlterEgo.2mg` | 819,264 | `4115CB7FB6D1CA9B68F6C82BE6D428BBEBB27A4934382929128B89B78870C912` | 800 KiB GS/OS boot disk, `/SYSTEM/START`, no Finder; Q → Y ends the game on the exit screen |
| `AlterEgo-full.2mg` | 3,670,080 | `3D7EA71E36ED892A7F77CE4D4F6381000D77E498F904CDD439DEACBE0308DCB0` | full System 6 volume, `/ALTEREGO/AlterEgoGS.S16`, Finder; Q → Y returns to the Finder |

The only open decision left was the tag name, and the candidate recorded on 2026-11-03 —
**`iigs-v0.0.2`** — is the one that shipped.  It is the engine snapshot's number rather than the
port's own; `README.md` already explains that the engine is silky-gs v0.0.2 (`0c341d2`), so the name is
consistent with the rest of the docs.

### What each disk carries — checked before publishing

Opened both images with Cadius and hashed the programs, instead of trusting the file names:

- `AlterEgo.2mg` → `/ALTEREGO/System/Start` (Cadius wants the volume-qualified path; `/SYSTEM/START`
  answers "Wrong volume name") = 316,161 B, SHA256 `505F861B…`, i.e. `build/AlterEgoGS.exit`, the
  `--exitscreen` build.
- `AlterEgo-full.2mg` → `/ALTEREGO/AlterEgoGS.S16` = 313,376 B, SHA256 `0F24BDE5…`, the default
  (Finder) build, the same bytes as `build/AlterEgoGS`.  It is current: the whole image is unchanged
  since 2026-11-04d, `3D7EA71E…`.

The `.po` is **not** a release asset: 「留 2mg就好, po檔可以不用了」.  `npm run make:po` stays as a local
convenience (`build/AlterEgo.po`, 819,200 B, `DDB3E9A5…`), and the docs now present the release as the
two `.2mg` files.  `HDV` was never shipped.

### Trap — the disk GSplus had been playing was not the shipped disk

GSplus (the user's session, started 14:04) had `iigs/build/AlterEgo.2mg` open, and the guest had
written `ae.prefs` (296 B) to the volume root: `Block : 1600  Free : 494  File : 16`, and the file
hashed `7A4DAA00…` instead of the committed `4115CB7F…`.  `git status` showed it as modified, so it was
restored with `git checkout -- iigs/build/AlterEgo.2mg` (no rebuild: the committed bytes are the
shipped bytes) and the release asset is that restored file.  This is the 2026-11-04c trap in practice:
`SavePrefData` writes to the disk the game ran from, so a *played* copy always differs from the packed
one.  `npm run test` boots a scratch copy under `tmp/test/` and left the image byte-identical before
and after the run.

### Verified before publishing

- `npm run test` on the committed `build/AlterEgo.2mg`: **PASS**, title after 5.5 s, Level 1 after
  2.3 s, same pixel signatures (grey 24 / orange 3132 / teal 28 and grey 9192 / teal 4688 / orange
  9260), image unchanged (`4115CB7F…` before and after).
- The user played that disk in GSplus and confirmed Q → Y shows the exit screen (2026-11-04d), which
  is the one manual step a harness cannot do here.
- `git status` clean apart from the untracked `Alter_Ego.nes`.

### Files touched

- `iigs/README.md` — release section retitled and rewritten around `iigs-v0.0.2` and the two `.2mg`
  assets; the `.po` is now explicitly "not part of the release"; free-block count corrected to 495.
- `README.md` — a **Download** bullet with the tag link and both hashes; the boot-disk bullet's program
  size corrected to 316,161 B and 495 free blocks; the `.po` bullet marked optional.
- `iigs/CHANGES.md` (2026-11-04e), this entry.

## 2026-11-04d — Q on the boot disk: a real exit screen, drawn in Super Hi-Res

The user picked the one-way exit over the restart (「1 看看吧」), and rejected the "keep restarting" and
"freeze on a black screen" alternatives — 「2,3 就跟win95 關機後顯示 "現在你可以關閉電腦"一樣啊XD 沒意義~」.
So Q → Y on the 800 KiB boot disk now stops the game for good and leaves a screen that says so.

### What the screen is

A 320×200 Super Hi-Res bitmap, rendered at **build time** from the game's own NES CHR font, and copied
to `$E1/2000` by the quit code:

```
ALTER EGO HAS EXITED
PRESS RESET TO PLAY AGAIN
THANKS FOR PLAYING
IT IS SAFE TO TURN OFF
```

White on black, the game's bold font, so it looks like it belongs to the game. No glyph for `Q` or `W`
exists in the font (`gen-credits.py`'s map: `A..P`, `R..V`, `X`, `Y`, `Z`, digits), hence "EXITED".

`QuitToExitScreen` (`Main.s`) is: `NES_Pause`, `SavePrefData`, `NES_ShutDown`, then border black, palette
0 = `$0000`/`$0FFF` (`$E19E00`, index 15 at `$E19E1E`), the 200 SCB bytes at `$E19D00` zeroed, the
picture copied, and `bra`-halt. The display is still SHR at that point (`NES_ShutDown` restores the mode
the game started in, `$C1`), so nothing has to be switched on.

### Why not a 40-column text screen — measured, and abandoned

That was tried first (a `Bye8` blob written to `$2000` and `jsr`-ed, then inline code) and it does not
work on this machine:

- It never executed at all until it was inline in `Main.s`: the blob had been assembled *before* the
  entry code, so it became the application's entry point and ran at start-up, not at quit. Every probe
  result from that period was invalid.
- Inline, the machine does switch to legacy video and the page does get written, but the video generator
  reads the page back with an offset and a stride that do not match a plain 40×24 Apple II page: on a
  24-row page, 25 displayed rows of 40 columns at 10 px per glyph came out shifted ~6 columns left and
  ~2 rows up, with rows permuted (`ruler/`, `ruler2/`, `ruler3/` probes: display rows read table rows
  0,3,6,… then 1,4,7,…, and `ROWnn` rulers re-displayed earlier rows instead of trailing blanks).
- None of the levers changed it: `$C00C` (drop to 40 columns), a fresh `$C029 = $00`, shadow off, both
  banks `$00/0400` and `$E0/0400` filled, `$C04A-$C04D` (fine/coarse scroll) zeroed.
- `_QuitGS` was ruled out earlier and stays ruled out: `$0000` → `Can't run next application.
  Error=$1E06` (nothing to hand off to), our own address → not entered, and there is no Finder here.

### The one thing that had to be measured: pixel order in a word

Four pixels live in one 16-bit word, and the order was not guessed: `--test` renders the same line in
each of four candidate orders, one band per row. On the boot disk (GSplus) only **`pairSwapped`** reads
as text, i.e. in memory **each byte holds two pixels, leftmost in the high nibble**, and the two bytes
of a word are the other way round from what `sta` of a 16-bit word writes. The generator keeps the
table (`PACKS`) and the measured comment.

### Space — bands, not the whole screen

The full 32,000-byte picture does not fit where the tile data is (`CHRDATA` is already a whole 64 KB
bank) and a ninth segment is off the table (the GS/OS S16 loader wants eight). So the generator emits
only the four **text bands** (8 rows × 160 bytes each, 5,120 bytes total) and the quit code clears the
screen first, then copies each band to the pixel row it was rendered at. `QuitScreen.s` is generated and
gitignored; `build.js --exitscreen` runs the generator before Merlin.

### Verified

- `--exitscreen --autotest` (a dev build that quits at start-up, so no key press is needed) packed into
  a scratch `.2mg`: the screen renders exactly as above, white on black, nothing left over from the game,
  and it stays up (`iigs/tmp/p8test/exit2/t14.png`).
- The **shipped** boot disk (`build/AlterEgo.2mg`) still passes `npm run test`: title after 9.8 s,
  Level 1 after 2.3 s, PASS.
- The **real key path** is confirmed: the user pressed Q → Y in GSplus on `build/AlterEgo.2mg` and the
  exit screen came up (「有gsplus 按q->y有顯示那個exited畫面」). The harness cannot drive `q` here — it
  does not reach GSplus, although `Return` does (`iigs/tmp/p8test/qexit/` shows the level still running
  after `q`) — so that press is the user's; the screen it produces is the one the autotest captured
  above. Key handling itself was verified on 2026-11-04c.

### Build flags

| Flag | Behaviour |
|---|---|
| (none) | full System 6 volume: `_QuitGS $0000`, back to the Finder (`build/AlterEgoGS`) |
| `--exitscreen` | one-way exit screen, **the boot disk** (`build/AlterEgoGS.exit`, packed by `make:boot`) |
| `--boot` | preferences + back to the title screen (still available, used by no shipped image) |
| `--autotest` | dev only: quit at start-up so the quit path needs no key press |

`make:boot` now runs `build.js --exitscreen`, so the boot image can never be packed from a copy that
quits to the Finder.

### Artifacts

| Item | Value |
|---|---|
| `iigs/build/AlterEgo.2mg` | 819,264 B, SHA256 `4115CB7FB6D1CA9B68F6C82BE6D428BBEBB27A4934382929128B89B78870C912`, 1,600 blocks, 495 free, 15 files |
| `iigs/build/AlterEgoGS.exit` (local) | 316,161 B, SHA256 `505F861B10C3A5045D3FE9F5BE7F3096CC9307A2E7B5C310D2D0605807AE35EC` |
| `iigs/build/AlterEgoGS` | 313,376 B, SHA256 `0F24BDE5FDE92B4548C684A5E1D1EF2915A5842BC77473AAC6B4A92AA6A0AB1B` (unchanged — reproduced byte for byte) |
| `iigs/build/AlterEgo-full.2mg` | 3,670,080 B, SHA256 `3D7EA71E36ED892A7F77CE4D4F6381000D77E498F904CDD439DEACBE0308DCB0` (unchanged) |

The `.2mg` hash above is the image exactly as `make:boot` last packed it.  Cadius stamps the ProDOS
directory entries with the time it ran, so packing the same inputs in a different minute gives a different
hash (measured: two packs a minute apart differ; two in the same minute are identical).  The
reproducible part is the application inside it, `AlterEgoGS.exit` `505F861B…`.

### Files touched

- `iigs/src/games/alterego/Main.s` — `QuitToExitScreen` (SHR palette/SCB/picture copy + halt), the
  `DO QUIT_EXITSCREEN` dispatch at `quit`, `put QuitScreen.s` in the data area, the comment above `quit`
  rewritten (the text-mode routine and its comment are gone).
- `iigs/scripts/make-quit-screen.mjs` (new) — renders `QuitScreen.s`; `--test` compares the four pixel
  orders, `--preview` prints a downsampled view.
- `iigs/src/games/alterego/build.js` — `--exitscreen`/`QUIT_EXITSCREEN`, runs the generator, publishes
  `AlterEgoGS.exit`; `--boot` kept for the restart variant.
- `iigs/scripts/make-boot-2mg.mjs` — builds and packs the `--exitscreen` copy.
- `iigs/.gitignore` — `QuitScreen.s` is generated; the `Bye8` entries are gone.
- Removed: `iigs/src/games/alterego/Bye8.s`, `iigs/dist/BYE8`, `iigs/scripts/make-bye8.mjs`,
  `iigs/tmp/p8test/make-vidprobe.mjs` (the abandoned text-mode experiment).
- `iigs/dist/README.TXT` — the boot disk's NOTES now say Q ends the game for good and only the reset
  button starts the machine again (CR line endings kept; the image was repacked after the edit).

## 2026-11-04c — Q on the 800 KiB boot disk: restart, not quit

Reported by the user, verbatim: 「看到了, 原來你直接放到 system目錄下的 start , 那若遊戲中按Q出來, 就當了」.
On the boot disk there is no Finder and no desktop, so Q → Y asked GS/OS for the next application and
it stopped on `Can't run next application. Error=$1E06`, sitting on that blue screen.

### What Q does now

One source tree, **two builds**, because what Q can do is a property of the disk:

- **`build/AlterEgoGS`** (`npm run build:alterego`, default): shuts down and calls `_QuitGS`, i.e.
  back to the Finder.  This is what the full System 6 volume has, and it is what the port always did.
- **`build/AlterEgoGS.boot`** (`node build.js --boot`, run by `npm run make:boot`): `NES_Pause` +
  `SavePrefData` + `NES_Resume` + `NES_WarmBoot`, i.e. the preferences are written and the game goes
  back to its title screen.  It is packed into `build/AlterEgo.2mg` as `/SYSTEM/START`, so the boot
  image cannot be assembled from a copy that quits.  The file is local (gitignored), the boot image
  is the tracked deliverable.

The switch is the generated `QuitMode.s` (`QUIT_RESTARTS equ 0|1`), written by
`src/games/alterego/build.js` before Merlin runs and `put` by `Main.s`; `quit` tests it with the code
base's `DO`/`ELSE`/`FIN`.  `Main.s` explains both sides in the comment above `quit`.

### Why not detect it at run time

Tried first, and abandoned after these measurements — the negative result is the useful part:

- `_OpenGS` on the Finder's pathname, called from the **quit handler**, failed for every candidate:
  `1/FINDER`, `2/FINDER`, `2/SYSTEM/FINDER`, `ALTEREGO/SYSTEM/FINDER`, `/ALTEREGO/SYSTEM/FINDER`, and a
  single-candidate probe `1/START` (the running program's own file) too.  So it was not a wrong path.
- Moved to **start-up**, before `NES_StartUp`, it works on the boot disk — `1/README.TXT` (a root
  file) resolves, which is how **prefix 1 was pinned to the boot volume's root** (not the app's
  directory, and not what `SAVE_FILENAME '1/ae.sav'` had always implied).  It failed on the full
  volume for `1/SYSTEM/FINDER`, `1/SYSTEM/START.GS.OS` and a sweep of `1/`…`9/SYSTEM/FINDER`, and for
  `/SYSTEM/FINDER` and `/ALTEREGO/SYSTEM/FINDER` — a path starting with a slash names a *volume*, not
  a root-relative path.
- Moved to just after `NES_StartUp`: still "no Finder" on the full volume.  And note that volume's
  game was launched by the **Finder** (`/SYSTEM/Start` was the game in the test copy), so the prefixes
  it inherits are the Finder's — 1 through 9 all missed the boot root.

A build switch has no such blind spot, and both shipped disks get the behaviour they can actually
support.

### Verified

- `build/AlterEgo.2mg` (boot disk), GSplus at `Limit: 16.0Mhz`: boot → title → `Q` (QUIT GAME box) →
  `Y` → **title screen again**, game continues; no `Can't run next application. Error=$1E06`.
  Captures: `iigs/tmp/qtest/03-after-y.png`, `04-later.png`.
- A full System 6 volume with the default build installed as `/SYSTEM/Start` → `Q`, `Y` → GS/OS
  relaunches its start application (the game) and the title comes back; the `$1E06` stop is gone.
  `iigs/tmp/qtest-full/`.
- `npm run test`: title after **9.9 s**, Level 1 after **2.3 s**, same pixel signatures, PASS.
- The keyboard harness (`iigs/scripts/gsplus-input.ps1`) now posts `WM_KEYDOWN`/`WM_KEYUP` instead of
  `keybd_event`; with it Q is delivered reliably, and the earlier "Q does nothing" sessions were the
  harness, not the game (Caps Lock was a red herring: `NES_EvtLoop` accepts `q` and `Q` alike).

### Trap — `npm run test` dirtied the shipped image

`test-alterego.mjs` used to boot `build/AlterEgo.2mg` itself, so the guest's writes (a preferences file
at the volume root) changed a tracked deliverable.  It now copies the image to `tmp/test/` and rewrites
`s7d1` to that copy, the same way it already used a scratch `.kegs` for `ssdir`; `build/AlterEgo.2mg`
is byte-identical before and after a run.

### Artifacts

| Item | Value |
|---|---|
| `iigs/build/AlterEgoGS` | 313,376 B, SHA256 `0F24BDE5FDE92B4548C684A5E1D1EF2915A5842BC77473AAC6B4A92AA6A0AB1B` (full-volume build: Q quits) |
| `iigs/build/AlterEgoGS.boot` (local) | 313,359 B, SHA256 `444E63AE1C9A34E33BCB1E17EFE06B661C2C77C1D117BBE9F97B9985BC26C174` (boot-disk build: Q restarts) |
| `iigs/build/AlterEgo.2mg` | 819,264 B, SHA256 `2B8F3011220C5E34139DE5566EC521833598D1B17FB8FA67D585B87EEA3BF251`, 1,600 blocks, 500 free, 15 files |
| `iigs/build/AlterEgo-full.2mg` | 3,670,080 B, SHA256 `3D7EA71E36ED892A7F77CE4D4F6381000D77E498F904CDD439DEACBE0308DCB0`, 7,168 blocks, 729 free, 185 files |

### Files touched

- `iigs/src/games/alterego/Main.s` — the `DO QUIT_RESTARTS` quit block, `put QuitMode.s`; the
  run-time `HasFinder` probe and its records are gone.
- `iigs/src/games/alterego/build.js` — `--boot`, `QuitMode.s`, publishes `AlterEgoGS.boot`.
- `iigs/scripts/make-boot-2mg.mjs` — builds the boot-disk copy itself and packs that.
- `iigs/scripts/test-alterego.mjs` — boot a scratch copy of the image.
- `iigs/.gitignore` — `QuitMode.s` and `AlterEgoGS.boot` are local.
- `iigs/dist/README.TXT` — the key sheet on the boot disk now says what Q does there ("EXIT GAME and
  Q (then Y) return to the game's title screen", "On a full System 6 disk Q (then Y) quits to the
  Finder instead"); the image was repacked after the edit.
- `iigs/CHANGES.md` (2026-11-04c, `Q` in the key table), `iigs/README.md` (Q on the boot disk,
  `make:boot` builds the copy), this entry.

## 2026-11-04b — release boot disk: 800 KiB, GS/OS boot set + the game only

The release image is now **819,264 bytes** — a 64-byte 2IMG header plus 1,600 blocks (800 KiB), down
from 3.5 MB: ProDOS 8, the minimal GS/OS 6 boot set and the game, nothing else.  GS/OS launches
`/SYSTEM/START` at boot and that file is the game, so there is no Finder and no desktop — booting goes
straight into the game.

### How — the silky-gs boot template, never a hand-built subset

`build/AlterEgo.2mg` is generated by `npm run make:boot` (`scripts/make-boot-2mg.mjs`):

- template **`dist/GSBoot.2mg`** (819,264 B): the silky-gs distribution's minimal GS/OS 6 boot disk,
  made by that repository's `scripts/make-boot-disk.js`.  It holds ProDOS, `Start.GS.OS`, `GS.OS`,
  `GS.OS.Dev`, `AppleDisk3.5`/`Console.Driver`, `Char.FST`/`Pro.FST`, `Error.Msg` and
  `System.Setup/{Resource.Mgr,Tool.Setup,TS2,TS3}` — 478 blocks, no Finder, no Tools, no CDEVs, no
  Icons.
- the script renames the volume to `ALTEREGO`, adds `build/AlterEgoGS` as **`/SYSTEM/START`** (staged
  as `Start#B3DB03`, so Cadius keeps ProDOS type S16 `$DB03`; 613 blocks), and adds `dist/README.TXT`
  at the root as a `$B0` ProDOS text file (CR line endings).  It then checks the catalogue (`Start
  S16` in `/SYSTEM`, `README.TXT $B0`, `Block : 1600`) because Cadius exits 0 even when `ADDFILE`
  fails.
- `/SYSTEM/START` is the name upstream's `build-single.bat` gives every game disk; GS/OS launches it
  at boot, so no `Start.Data` pointer is needed.

A 800K volume assembled by hand from the 3.5 MB image's files does **not** boot: GS/OS stops with
"Sorry, system error $0046 occurred while loading the start PSI file" because the subset misses boot
files — that was the 2026-11-03 attempt.  The template is a boot set that is known to boot.

### Verified

- `npm run test` on the 800 KiB disk: title after **9.9 s** (the 3.5 MB volume needs 12.2 s, because
  GS/OS loads the whole System 6 and the Finder there), Level 1 after **2.3 s**, same pixel
  signatures (grey 24 / orange 3132 / teal 28 and grey 9192 / teal 4688 / orange 9260), PASS.
- GSplus at `Limit: 16.0Mhz` with `s7d1` = `build/AlterEgo.2mg`: title, then Level 1
  ("HELLO WORLD") on the first Return — captures in `iigs/tmp/slim/shots800/`.
- `cadius CATALOG`: 1,600 blocks, 15 files, **500 free**; `CHECKVOLUME` reports nothing.

### Artifacts

| Item | Value |
|---|---|
| `iigs/build/AlterEgo.2mg` | 819,264 B, SHA256 `4E428232…`, 1,600 blocks, 500 free |
| `iigs/build/AlterEgo-full.2mg` | 3,670,080 B, SHA256 `7F0567BF…`, the 3.5 MB System 6 volume |
| `iigs/build/AlterEgo.po` (generated) | 819,200 B, SHA256 `8D7EB229…`, 1,600 blocks |
| `iigs/dist/GSBoot.2mg` | 819,264 B, SHA256 `B7E01149…` |
| `iigs/build/AlterEgoGS` | 313,359 B, SHA256 `88281425…` (unchanged) |

### Files touched

- `iigs/scripts/make-boot-2mg.mjs` (new), `iigs/package.json` (`"make:boot"`),
  `iigs/dist/GSBoot.2mg` and `iigs/dist/README.TXT` (new, tracked), `iigs/build/AlterEgo.2mg` (the
  800 KiB image), `iigs/build/AlterEgo-full.2mg` (the 3.5 MB image, renamed), `iigs/.gitignore`
  (allowlist entry for the full image).
- `iigs/README.md` (boot image, rebuild and release sections), root `README.md` (image and `.po`
  bullets), `iigs/CHANGES.md`, this entry.
- `iigs/scripts/trim-2mg.mjs` now defaults to `build/AlterEgo-full.2mg`; `iigs/build/AlterEgo.po` is
  regenerated locally and stays gitignored.

## 2026-11-04 — boot image trimmed 10 MB → 3.5 MB (`npm run trim`)

The image had grown out of a stock 10 MB ProDOS volume; System 6 plus
`/ALTEREGO/AlterEgoGS.S16` only fill 6,439 of its 20,480 blocks, so ~7 MB of every release file was
empty volume.  It is now **7,168 blocks / 3,670,080 bytes**, the smallest 0.5 MiB multiple that still
contains the highest allocated block (7,127).

### How — patch and truncate, never repack

`iigs/scripts/trim-2mg.mjs` (`npm run trim`, in place, idempotent) reads the 2IMG header, finds the
volume's allocation bitmap and rewrites three size fields:

- **bitmap location.**  The volume directory file starts at block 2 and chains through `next` (block
  offset `+2`) to its last block; block 5 here, so the bitmap starts at **block 6**.  It is
  `ceil(total/4096)` blocks (5 for 20,480, 2 for 7,168), one bit per block, **0 = in use, 1 = free**
  (confirmed against the image: block 6 starts `00` for the boot/header/dir/blocks-11-onward, block 10
  — past all data — is `FF`; counting 0 bits gives 6,439, which is exactly `cadius CATALOG`'s
  `Free 14041`).  The *total-blocks* word is at block 2 offset **`$29`** in every reference volume
  (`ALTEREGO` 0x5000, `GSBoot` 0x0640, ProDOS 2.4.3 0x0118) — it is *not* at the same offset as the
  date fields, which is what made the first attempts guess wrong.
- **patch**: volume header total blocks (`$29`), bitmap bits at/after the new end set to 0 (in use) so
  nothing can allocate past the volume, and the 2IMG header's block count (`+20`) / data size (`+28`)
  / file truncation.  Nothing else is touched: file data, resources forks and GS/OS extended entries
  come along byte for byte.
- **the old bitmap blocks.**  Blocks 8-10 were bitmap blocks of the 20,480-block volume; the smaller
  volume no longer needs them.  They are left **allocated** on purpose — freeing them made
  `cadius CHECKVOLUME` report the *inverse* complaints (it then called blocks 13-15 free although
  they hold `/ALTEREGO/BASIC.System`), so the conservative state is the one that boots.  Result:
  `CHECKVOLUME` reports exactly those three as "in use but not referenced" and nothing else.
- Anything that re-creates the volume instead (Cadius `CREATEVOLUME` + `ADDFOLDER`/`ADDFILE`) risks
  dropping forks and the GS/OS extended entries, so the script deliberately never does that.

### Verified

- `npm run test` on the trimmed image: title after **12.2 s**, Level 1 after **2.3 s**, same pixel
  signatures as before (grey 24 / orange 3132 / teal 28 and grey 9192 / teal 4688 / orange 9260), PASS.
- `cadius CATALOG`: 7,168 blocks, **729 free**, **185 files**, **11 directories** — identical file
  list to the 10 MB image (compared line by line; the only difference is the totals row).
- The script is deterministic: trimming the 10 MB backup again reproduces the tracked file byte for
  byte (SHA256 `7F0567BF…`), and a second run on the trimmed image is a no-op.

### Artifacts

| Item | Value |
|---|---|
| `iigs/build/AlterEgo.2mg` | 3,670,080 B, SHA256 `7F0567BFA1B9E118FF969A753E64B644B7989022D7D56A1BA58A31F5D86013B7` |
| `iigs/build/AlterEgo.po` (generated) | 3,670,016 B, SHA256 `5E4E56A56E55530EF786A3CAB454E2BC375B0C6FA935438B5953BE54CAFB7121` |
| `iigs/build/AlterEgoGS` | 313,359 B, SHA256 `88281425…` (unchanged) |

### Files touched

- `iigs/scripts/trim-2mg.mjs` (new), `iigs/package.json` (`"trim"`), `iigs/build/AlterEgo.2mg`.
- `iigs/README.md` (image size, printed `make:po` output, trimming note), root `README.md` (image size,
  `.po` block count), `iigs/CHANGES.md`, this entry.
- `iigs/build/AlterEgo.po` is regenerated locally (`npm run make:po`) and stays gitignored.

## 2026-11-03 — upstream triage (Lucas), silky-gs issue 29 (refiled as 46), 16 MHz release baseline

### Upstream triage — Lucas Scharenbroich's five suggestions, checked against this port

Lucas replied on Slack (#gte) with five suggestions for speeding up silky-gs games.  Each was checked
against the sources, not assumed:

- **8x16 fused sprites** (upstream `a15445c`, `SPR_TALL`): **not applicable**.  Alter Ego is 8x8-only
  — `Alter_Ego.nes` has header `flags6 = 0x01` (bit 5 clear), `prg-src/crt0_silky.s` programs PPUCTRL
  as `%10000000`, and `_oam_spr`/`_oam_meta_spr` emit 8x8 entries — so the fused 8x16 path never runs
  for this game.
- **No double dispatch for shims** (upstream `6502e55`/`62b7ae0`, PPU shadow variables moved into the
  NES bank): this port already dispatches through the in-bank `$7E00` `JMP` table, so there is no
  cross-bank fetch of the table, but every entry still ends in `jsl` into the engine bank.  Removing
  that `jsl` would save a few cycles per call; this game makes a handful of shim calls per frame
  (PPUCTRL/PPUMASK, 2x PPUSCROLL, 1x OAM DMA), which is ~100 cycles of the 46,666-cycle frame
  (<0.5%).  Not worth a re-base on its own.
- **`OAM_END_INDEX`**: already 64 and genuinely full — enemies 0-15, pause metas 16-31, particles
  48-51, stats 52-59, player 16x16 meta 60-63, so slot 63 is live and there is nothing to trim.
- **"Disable the attribute/colour-cycle twinkle"**: the mechanism is different here.  The stars are
  drawn once in `game_add_background`, and the only animated background is the sea, which rewrites
  nametable **tile indices** every 16 frames (`vram_adr`/`vram_put`) — no attribute writes and no
  colour cycling.  The analogue would be an optional sea-animation toggle, not a fix.
- **FPS meter / GSSquared / bootable disk**: the engine's meter exists (`config_video_fps`, VIDEO
  menu) but `CONFIG_VIDEO_MENU equ 0` hides that menu in this game; GSSquared is installed at
  `C:\dev\emu\gssquared\GSSquared.exe`; the bootable `.2mg` this port already ships covers upstream's
  new boot-disk target.  Lucas's point that GSPort/GSplus fps is not a hardware proxy is correct, and
  matches the 2.8 MHz measurements below (the emulator caps at 2.55 MHz effective on this VM).

### Upstream issue filed

<https://github.com/lscharen/silky-gs/issues/46> — "Pre-built/embedded compiled sprites: data point
from a CHR-ROM port (Alter Ego)".  This game is `HAS_CHR_RAM equ 0` (NROM, fixed 8 KB CHR-ROM), i.e.
the case that optimisation targets.  The issue carries the observation that the v0.0.2 sprite compiler
is already lazy and cached per (tile, palette, flip) and dispatched through `SPR_COMP_TBL`, so
pre-building would buy **startup** and cache-miss time, not steady state, plus three design questions
(scope, CHR-layout assumption, runtime fallback).

It was filed first as <https://github.com/lscharen/iigs-game-engine/issues/29> and that was the wrong
repository: lscharen closed it as completed the same day — "This issue was opened in the wrong
repository. Items related to the Silky-GS NES runtime should be opened in the `silky-gs` repository."
The runtime is what the request targets, so it was refiled in `silky-gs` on 2026-11-04 (and #29 got a
comment pointing at the refile); keep `issues/46` as the live link in anything written from here on.

The tile-renderer question is drafted in `docs/upstream-issues/tile-renderer.md` and is deliberately
**not** filed: upstream says that renderer is "not close to ready", and the only thing we need from it
is whether it changes the PPU shadow/queue ABI (this port is a v0.0.2 snapshot with its own `$7E00`
shim table, so an ABI change is a porting pass).

### Decision — no re-base onto upstream `main`

Upstream `main` is `aae8fed`; this port is pinned at the v0.0.2 tag (`0c341d2`), 21 commits behind.
Of the intervening work only the shim change would apply here (<0.5% of a frame, above) and the
sprite-compiler change does not exist yet; nothing in those commits fixes a defect this port has.
Adopting them means porting `rom_inject.s`'s rewritten shim layer and `ppu_reg_vars.s` against this
port's own `neslib_silky.s` / `silky_shims.inc` ABI — high risk, no measured gain.  Revisit if the
pre-built sprites land, if a port-visible bug appears upstream, or if a frame budget ever gets tight.

### Decision — release speed baseline: 16 MHz

The port is released for a **16 MHz** machine.  That is what the checked-in GSplus configuration, the
`docs/screenshots/` captures and `npm run test` use (boot to title ~20 s).  It also runs on a stock
**2.8 MHz** IIgs — gameplay renders at about 30 fps and the boot takes 2-3 minutes, so it is playable
rather than pleasant — and an accelerator in between (TransWarp GS, 7.1 MHz) sits proportionally
between the two: the renderer's per-frame cost is fixed, so smoothness scales roughly with the clock.
`README.md` and `iigs/README.md` now say exactly that; no source or artifact changed.

### Release images — `.2mg` for the IIgs release, `.po` on request

The IIgs release is the **`.2mg`** in `build/`.  Its payload is a 64-byte 2IMG header followed by the
ProDOS blocks in ProDOS order (`format = 1`), so an emulator that wants the bare volume takes those
same blocks as a **`.po`** — no conversion, no size change (10,485,760 bytes = 20,480 blocks).  New
`npm run make:po` (`scripts/make-po.mjs`) writes **`build/AlterEgo.po`** and refuses anything that is
not a 2IMG/ProDOS-order/whole-block image or that lacks the `ALTEREGO` volume name, so a bad image
cannot be shipped silently.  An HDV is that same file under the Apple II / IIe hard-disk name; the
IIgs release ships `.2mg`/`.po`, so no HDV is produced here.

- Verified end to end: a throw-away kegs with only `s7d1`/`ssdir` changed boots `build/AlterEgo.po`
  in GSplus at `Limit: 16.0Mhz` — title after ~12 s, Level 1 ("HELLO WORLD") on the first Return.
  Screenshots: `iigs/tmp/po/shots/gsplus_screenshot_20261103_172930.png` (title) and
  `..._172937.png` (Level 1).  The generated file hashes `8D2B5B36…`, the same bytes the `.hdv` run
  booted earlier, so the `.po` and the earlier hard-disk test are one image.
- The `.po` is the 10 MB ProDOS 8 volume (`ALTEREGO`, `/ALTEREGO/AlterEgoGS.S16`) with System 6, so
  mount it as a ProDOS disk and boot at **≥ 7.1 MHz** (16 MHz is the release baseline); at the
  factory 2.8 MHz setting it still boots, at the 2.8 MHz cadence (about 30 fps).
- `build/AlterEgo.po` stays **generated and gitignored** — the `build/` allowlist tracks only
  `AlterEgo.2mg` and `AlterEgoGS`.  The `.2mg` remains the source of truth (`npm run test` still
  boots it), and the `.po` is one `npm run make:po` away from it, so the two cannot drift.

### Files touched

- `README.md`, `iigs/README.md` — speed/requirements wording (16 MHz baseline, 2.8 MHz playable,
  accelerators in between) and the `.po` recipe.
- `iigs/CHANGES.md` — the day's entry.
- `iigs/scripts/make-po.mjs`, `iigs/package.json` — `make:po`: derive + validate the bare `.po`.
- `iigs/docs/upstream-issues/compiled-sprites.md`, `tile-renderer.md` — the filed issue text (for the
  record, with its URL) and the unfiled tile-renderer draft.
- No source, `prg.bin`, `AlterEgoGS` or `.2mg` change: the artifacts are byte-identical to 2026-11-01
  (`AlterEgoGS` `88281425…`, `.2mg` `93A3004F…`, `prg.bin` `C4CB0445…`).  `build/AlterEgo.po` is
  generated from the `.2mg` and not committed.

## 2026-11-02 — repository layout: root mirrors upstream, ports moved into subdirectories

- The repository root now matches upstream `avshabanov/alter-ego` again (`LICENSE`, `Makefile`,
  `.gitignore`, `src/`; only `README.md` differs), so the shared NES sources are upstream's and the
  Apple //e edits that used to sit in `src/game.c` are archived at
  `vera/docs/archive/apple2e/src-game-2026-11-02.c`.
- Everything for this port stayed under `iigs/`, but the deliverable moved from the repository-level
  `build/iigs/` into **`iigs/build/`**: `AlterEgo.2mg` and `AlterEgoGS` keep their bytes (verified
  after the move: `node scripts/test-alterego.mjs` passes, title after 10.0 s, Level 1 after 2.3 s),
  and `build.js` now publishes to `iigs/build/`.  Paths updated in `build.js`,
  `scripts/test-alterego.mjs`, `emu/gsplus-alterego.kegs` (`s7d1` → `C:\dev\alter-ego\iigs\build\AlterEgo.2mg`),
  `README.md`, `CHANGES.md` and `package.json`.
- Ignore rules for this tree are in `iigs/.gitignore` (root `.gitignore` is upstream's): `build/`
  tracks only the two deliverables, and `/tmp/` plus `__pycache__/` stay local.
- The dated entries below quote the pre-move (`build/iigs/...`) and pre-rename paths as labels; use
  the layout above for anything current.


## 2026-11-01g — full play-through reported normal

- The user played the port from boot through the ending on 2026-11-01 and reported nothing wrong
  (「從頭玩到尾也都正常」), after the new `npm run test` had passed.  That exercises levels 1–5, LEVEL
  CLEAR and the WELL DONE ending in practice, including the palette layouts the earlier entries list
  as screenshots-but-not-yet-captured.
- No captures were taken during that pass, so the repository still has no screenshot of GAME OVER,
  WELL DONE, LEVEL CLEAR or levels 2–5 — that is now purely a documentation gap, not an open defect.
  `README.md` (`### Verification`) and "Next steps" say so explicitly instead of implying those
  screens were never seen.
- Nothing else changed: no source, no artifacts, no build recipes.

## 2026-11-01f — `npm run test`: GSplus smoke test

- **New entry point.**  `iigs/package.json` now has `"test": "node scripts/test-alterego.mjs"`
  (the engine's vitest suite moved to `"test:unit"`, which it already had) and
  `"build:alterego": "cd src/games/alterego && node build.js"`.
- **What it asserts.**  Boot `build/AlterEgo.2mg` in GSplus, wait for the title screen, press
  **Return** once, wait for Level 1 — and check *pixels*, not just that the process is alive.  The
  signatures are colours that only appear in quantity on the screen they belong to, measured on the
  reference captures: title = grey 24 / orange 3132 / teal 28 (no grey playfield frame, big orange
  logo), Level 1 = grey 9192 / teal 4688 / orange 9260 (grey frame + teal water).  Thresholds sit far
  from both sets (`title`: grey < 500, teal < 500, orange 1500-7000, white >= 2000; `level1`:
  grey >= 4000, teal >= 1500), so animation frames (PRESS START blink, sea toggle) cannot flip a
  verdict.
- **How it captures.**  GSplus' own **F10** screenshot rather than `CopyFromScreen`: it writes a clean
  704×528 RGBA PNG with no desktop/window chrome and no dependence on where the window sits, and it
  works even if another window covers the emulator.  The script copies `emu/gsplus-alterego.kegs` into
  `tmp/test/` with `ssdir` pointed there, so the tracked `.kegs` and `docs/screenshots/` stay clean;
  each capture deletes its file and keeps `title.png` / `level1.png` only.
- **Keyboard.**  GSplus only reads the keyboard while its window is focused, so every key goes through
  `scripts/gsplus-input.ps1` (Windows PowerShell 5.1 is the only `powershell` here — there is no
  `pwsh`), which does `SetForegroundWindow` then a 90 ms `keybd_event` tap.  Actions: `window`,
  `focus`, `f10`, `return`, `tab`, `space`, arrows (arrows use the extended-key flag, as before).
- **No npm dependencies.**  `test-alterego.mjs` decodes the PNG itself with `node:zlib` (8-bit,
  non-interlaced, colour types 2/6, all five filter types), so it runs without `node_modules`.
- **Measured.**  `npm run test` on the shipped image, GSplus at `Limit: 16.0Mhz`: title after 12.1 s,
  Level 1 after 2.3 s, exit 0.  Options: `--keep` (leave it running for inspection),
  `--boot-timeout <s>` (default 180 — a 2.8 MHz build needs minutes), `--level-timeout <s>`
  (default 120); `AE_GS_GSPLUS` overrides the emulator path.  Captures land in `iigs/tmp/test/`, which
  is now gitignored together with the repository's `tmp/`.
- It does **not** rebuild: it checks whatever `build/AlterEgo.2mg` currently holds, so run
  `npm run build:alterego` + the Cadius `REPLACEFILE` recipe first if the application changed.

## 2026-11-01e — repository renamed to `alter-ego`

- The repository (and the local checkout) is now **`alter-ego`** (was `alter-ego-vera`), because it
  hosts two Apple II targets: the VERA port at the root and this IIgs port under `iigs/`.  The
  checkout path is `C:\dev\alter-ego`, and every documented path was rewritten to match.
- Git history, branches and artifacts are untouched: the VERA release images keep their
  `alter-ego-vera*` filenames (artifact names, not the repository name) and the IIgs deliverable stays
  `build/AlterEgo.2mg`.
- `README.md` now leads with a two-target table instead of "Apple II VERA Port"; the root `AGENTS.md`
  records the rename.
- Until the rename is done in the GitHub web UI (Settings → Rename repository), `origin` keeps the old
  URL; afterwards it becomes `https://github.com/anomixer/alter-ego`.

## Status at 2026-11-01

- **`test/gs` was fast-forward merged into `master` on 2026-11-01** and then deleted,
  so the port is now on the repository's mainline, which is the only branch left; `master` is the
  default branch on GitHub.
- `build/AlterEgo.2mg` boots in GSplus; verified: title, credits, sound test, pause menu, level 1,
  and the game → pause → EXIT GAME → title round trip.  `npm run test` covers the boot → title →
  Level 1 path automatically (2026-11-01f), and the user played the port from boot to the ending on
  2026-11-01 and reported it normal (2026-11-01g), so levels 2–5 and the ending screens are confirmed
  in practice.  Current hashes are in the 2026-11-01c entry (hashes quoted in older entries are older
  artefacts); rebuild recipes are in "Rebuilding `prg.bin` from the C sources".
- **The deliverable moved out of `iigs/` on 2026-11-01**: the boot image and the S16 application now
  live in `build/`, next to the VERA port's images in `vera/build/` — see the 2026-11-01c
  entry.  Older entries below quote the pre-move paths (`iigs/emu/…`, `iigs/src/games/alterego/…`).
- Boot image renamed `AlterEgoJml.2mg` → **`AlterEgo.2mg`** (and the kegs to `gsplus-alterego.kegs`)
  — see the 2026-11-01 entry.  The volume and program names inside the image did not change.
- Level-start music hold: the level music keeps playing on **LEVEL CLEAR**, is paused from the switch
  into the next level (black load screen) through the READY blink, and comes back when the player has
  control — see the 2026-10-31 entry.  The user play-tested it and approved.
- Sound test: **Tab** opens and closes it, row 23 reads `MUSIC ON  SFX00 BGM00`, the selected pair is
  pale yellow, **Left/Right** pick the field, **Up/Down** change the value, **Space** (or X) auditions
  it, **Z** stops the music, **Return** leaves and starts the game.
- Known gap: on the user's machine X/Z still need Caps Lock; the shim accepts every encoding tried and
  GSplus runs fine without Caps Lock, so that layer was not changed again — the sound test no longer
  depends on X/Z (see "Open issue" below for the pending diagnostic).
- Exchange-move sea stripes: **fixed and reproduced/verified** (see the 2026-10-30b entry below).
- Credits screen: rows tightened, the IIgs credit added, held 6 s — see the 2026-10-30c entry.
- 2.8 MHz: renders fit in one VBL (`renderVblTicks` = 1) and music is VBL-driven at 60 Hz — measured,
  not assumed; details in the same entry.

## 2026-11-01d — PRG staging tree imported; upstream tree archived

- The Apple //e / upstream working tree `C:\dev\alter-ego` was **removed on 2026-11-01**.  Before it
  went, the parts that existed nowhere else were imported:
  - its `build/silky` PRG staging tree became **`iigs/prg-src/`** (sources + the objects the shipped
    `prg.bin` was linked from; the screenshots and the `game_menu*` / `prg_*` experiment variants were
    left behind).  Verified: the documented `ld65` line there reproduces `prg.bin` **byte for byte**,
    32,768 bytes, SHA256 `C4CB0445…`.
  - `vera/docs/PORT-APPLE2-EVAL.md`, `docs/PORT-IIGS-SILKY-EVAL.md`, `docs/PORT-IIGS-TITLE-POC.md` and
    `build/level0_dhgr.png` moved up into `docs/`.
  - the //e work was archived under **`docs/archive/apple2e/`**: the *uncommitted* `src/game.c`
    rewrite (`src-game.c`), the //e `AGENTS.md` / `README.md`, and the //e investigation tools
    (`a2_emu.py`, `a2_art.py`, `dos33_pack.py`, the AppleWin automation scripts, …).  See
    `docs/archive/apple2e/IMPORT-NOTES.md` for what was deliberately dropped (`tools/a2run` 350 MB,
    the 219 MB `build/` outputs, and two local-only commits on its `test/gs` branch).
- Consequently the "built elsewhere" wording in the `prg.bin` recipe is obsolete: the staging tree is
  now in this repository, and `iigs/README.md` / the recipe below point at `iigs/prg-src`.
- `iigs/src/games/alterego/neslib_silky.s` and `iigs/prg-src/neslib_silky.s`, and the two
  `game_apop1.c` copies, are still duplicates that must be kept byte-identical (documented above).

## 2026-11-01c — deliverable moved to `build/`

- Artefacts now live outside the source tree, aligned with the VERA port's `vera/build/`:
  - `iigs/emu/AlterEgo.2mg` → **`build/AlterEgo.2mg`** (boot image, tracked),
  - `iigs/src/games/alterego/AlterEgoGS` → **`build/AlterEgoGS`** (S16 application, tracked),
  - `iigs/emu/AlterEgoOld.2mg` → `build/AlterEgoOld.2mg`, then **deleted** the same day: it is the
    2026-10-29 image (application 313,192 B, SHA256 `0C4005C5…`) and predates the 2026-10-31 music hold,
    so keeping it only invited confusion.  Nothing tracked ever referenced it.
  The GSplus configuration stays at `iigs/emu/gsplus-alterego.kegs`; its `s7d1` now points at
  `C:\dev\alter-ego\build\AlterEgo.2mg`.
- `src/games/alterego/build.js` now **publishes** the assembled load file: after `buildNromGame`
  (which compacts Merlin32's DSK in place in the game directory) it copies `AlterEgoGS` into
  `build/`.  Merlin32 still writes its DSK and listings into `iigs/src/games/alterego/`, which is
  now ignored (`.gitignore`: `/src/games/alterego/AlterEgoGS`) so a rebuild does not dirty the tree.
- Root `.gitignore` gained the `/build/` allowlist mirroring the `a2vera` block, so
  `AlterEgo.2mg` and `AlterEgoGS` are tracked while everything else in that directory stays local.
- Repackage and run recipes updated to the new paths (`build\AlterEgoGS` →
  `tmp\repackage\…`, `REPLACEFILE build\AlterEgo.2mg`).
- Verified after the move: `node build.js` prints
  `C:\dev\alter-ego\iigs\src\games\alterego\AlterEgoGS: 387398 -> 313359 bytes` and
  `published ..\..\..\build\AlterEgoGS`; the image was repacked from that file and GSplus boots
  it to level 1 on the first Return (`try 0: score=365`).
- Current artefacts: **`build/AlterEgo.2mg`** 10,485,824 B, SHA256 `93A3004F…`; **`build/AlterEgoGS`**
  313,359 B, SHA256 `88281425…`.  The application bytes are identical to the pre-move build (the rebuild
  reproduced them exactly — the Merlin link is deterministic here), so the image only changed because
  Cadius rewrote the directory entry when it was repacked (its SHA256 therefore no longer matches the
  `370D665E…` quoted in the 2026-10-31/2026-11-01 entries).

## 2026-11-01 — boot image renamed: `emu/AlterEgo.2mg`

- `iigs/emu/AlterEgoJml.2mg` → `iigs/emu/AlterEgo.2mg` and `iigs/emu/gsplus-alterego-jml.kegs` →
  `iigs/emu/gsplus-alterego.kegs` (`s7d1` updated).  No bytes inside the image change, so its SHA256
  stays `370D665E…`; only the filename moved.  `AlterEgoOld.2mg` is still the untracked older image.
- Where "Jml" came from: it is a leftover working label from the earlier `C:\dev\silky-gs` tree (which
  also had `AlterEgoJml2.2mg` next to `AlterEgoOld.2mg`), from that tree's `JML` boot experiments —
  `scripts/make-boot-disk.js` builds minimal boot images whose boot sector `JML`s into the program
  instead of going through `BASIC.System`/Finder.  This image is not one of those (it is a stock
  ProDOS 8 / System 6 disk with `/ALTEREGO/AlterEgoGS.S16` installed), so the suffix said nothing
  about the game; it is gone now.
- All references updated in `AGENTS.md`, `README.md`, `CHANGES.md`, the kegs file and the throw-away
  `iigs/tmp/*.kegs` copies.  Verified after the rename: booting `gsplus-alterego.kegs` in GSplus
  reaches level 1 on the first Return (`try 0: score=365`).

## 2026-10-31 — level-start music hold (screen off → READY blink)

The requirement, verbatim: 「顯示 LEVEL CLEAR 的時候, 還是可以播放音樂. 但切換到下一關到人物閃完這個
過程中, 先暫停音樂」.  So the music must keep playing on the LEVEL CLEAR screen and be silent **only**
from the switch into the next level (the black load screen) until the ego has finished the READY
blink, then return when the player has control.  An earlier plan (mute on every level-clear
transition) was wrong for this reason.

### Implementation — engine side, `prg.bin` untouched

All of it is in `src/rom/rom_exec.s` (MAIN), so it needs no ROM rebuild:

- `vblWork` (every VBL) samples the engine's `ppumask` mirror — the byte the ROM wrote through
  `PPUMASK_WRITE` — into `musicMask`.  A non-zero → zero transition is the ROM's `ppu_off()`: start
  the hold at `MUSIC_HOLD_LOAD` (900 frames; only a safety cap).  Zero → non-zero is
  `ppu_on_all()`: if a hold is already running, re-arm it to `MUSIC_HOLD_START` (52 frames), so the
  load time does not matter.
- While `musicHold` ≠ 0 the VBL sets FamiTone2's pause bit, `$0101` bit 7 of the ROM's own RAM (the
  AEROM bank) — the same bit `FamiToneMusicPause` (`$A915`, `AA AD 01 01 … 8D 01 01 60`) uses — and
  raises `apu_suspended` so the note that is sounding is cut instead of hanging.  The bit must be
  re-asserted every frame: the level's `music_play` writes `$0101` from the module and clears it.
- `nesRunNMI` (once per NES **frame**, before the ROM's NMI handler runs `FamiToneUpdate`) counts
  `musicHold` down and clears bit 7 when it reaches zero.  Counting NES frames rather than VBLs is
  what makes it line up with the ROM's `start_delay = 50` blink: that blink runs at ~27 frames/s on
  this machine, so 52 NES frames ≈ 2.4 s of wall time and the music starts on the frame the ego
  becomes controllable, at the first row of the level song.
- `ppu_regs.s`: `ppumask` is now `ENT` (it was segment-local) and `ImportEngine.s` imports it, so MAIN
  can read the mirror.
- LEVEL CLEAR has no `ppu_off()` anywhere: `game_apop1.c` turns the screen off only at 648 (credits),
  674 (title), 929 (game over), 955 (well done) and 1103 (`game_loop`'s level load).  The hold can
  therefore never start on the LEVEL CLEAR screen and its music is untouched.
- Same rule applies to every screen with a screen-off/screen-on pair, so the title, credits and
  game-over music now come back ~52 frames after their screen turns on (about 1 s at 54 fps, closer
  to 2 s where the first frames are slow).  Accepted; `MUSIC_HOLD_START` / `MUSIC_HOLD_LOAD` are the
  two knobs if that ever needs shortening.

### Trap found while implementing — write `$0101` one byte wide

The first version used `ldal ROMBase+$0101 / ora #$80 / stal ROMBase+$0101` with 16-bit A, so the
store also wrote `$0102` and the unpause path's `and #$7F` zeroed `$0102`.  The game then froze on
the title screen: the title was drawn, Return did nothing, 12 automated tries all `score=0`, while
the shipped build reaches level 1 in one try with the same harness.  Fix: wrap the access in
`sep #$20` … `rep #$20` so only `$0101` is read and written — which is also what the ROM itself does.

### Verified

- 16 captures 300 ms apart through a level start, with a temporary "white border while `musicHold`
  ≠ 0" probe (removed again): title with the normal border → black load screen with a **white**
  border (hold active) → level drawn with the ego blinking, still white → border back to normal on
  the first frame the ego is drawn and controllable.  `iigs/tmp/bench/burst1/b06.png` (hold during
  the black load screen), `b12.png` (hold released, ego visible).
- `iigs/emu/AlterEgo.2mg` repacked with the new `AlterEgoGS`; boots in GSplus at `Limit:16.0Mhz`
  and reaches level 1 on the first Return (`try 0: score=365`,
  `iigs/tmp/bench/emucheck/l00.png`).
- LEVEL CLEAR itself is not captured (the harness cannot clear a level); it is covered by the static
  check above — no `ppu_off` in that sequence, so no hold can start there.

### Files touched

- `src/rom/rom_exec.s` — `musicHold` / `musicMask` / `musicPaused`, the hold logic in `vblWork`, the
  frame countdown and unpause in `nesRunNMI`, `apu_suspended` OR; `bne :out` became
  `beq :no_skip / jmp :out` (Merlin's 127-byte branch limit).
- `src/games/alterego/ppu/ppu_regs.s` + `src/ppu/ppu_regs.s` — `ppumask ENT`.
- `src/ImportEngine.s` — `ppumask EXT`.
- `AlterEgoGS` 313,359 B, SHA256 `88281425E7458E38589446267966A1AE8F86DA0478D612F07306FA91F4FEB764`;
  `emu/AlterEgo.2mg` (10,485,824 B) repacked with it, SHA256
  `370D665E732BEB5FF4A75FB5986D2D5999E686F43DE1A305527C78D50B0EE6DF`; `prg.bin` unchanged
  (`C4CB0445…`).  The .2mg/app are not byte-reproducible across rebuilds — compare `prg.bin`.

## 2026-10-30b — exchange-move sea stripes fixed; 2.8 MHz performance measured

### Bug — stray stripes in the sea during the A/B exchange move

- **Root cause**: the swap sets `player_flash_cnt=2` on every frame while the two egos move
  (`game_apop1.c`, `player_exchange==1`), and the NES flash wrote `pal_col($3F15..$3F17)`
  alternating `$21`/`$27`.  Those NES sprite-palette entries alias onto the IIgs SHR slots the
  background palettes also fill (`BG2` uses slots 0,7,8,9, `SP1` 0,3,7,9, `SP2` 0,13,14,3), so
  the flash recoloured the water.  The 50-frame `DONE_NOLUCK` flash did the same.
- **Reproduced twice, once through the real code path**:
  - unconditional `pal_col` replay: whole sea band orange-striped —
    `docs/screenshots/exchange_sea_before.png` (8,000 px of `255,170,68` replacing the blue rows);
  - the decisive run: keep the *original* flash code and force the game's own trigger
    (`i|=PAD_A; exchange=5;` every 64 frames in the play loop, so the swap / blocked-swap flash
    runs as it does for a player).  46 captured frames at 2.8 MHz → **23,696 orange px** in the
    sea band, up to **2,780 px in one frame** (`docs/screenshots/exchange_sea_old_path.png`).
    Same harness with the fixed flash → **0 orange px in all 46 frames**
    (`docs/screenshots/exchange_sea_fixed_path.png`, and `..._wave.png` mid wave-toggle).
- **Fix**: no palette writes and no palette-bit switching — the flash blinks the ego sprites
  (see "Follow-up: the flash must not repaint the ego either" below for the final form).
- The bug is intermittent because a `pal_col` change makes `DetectNESPalette` miss, so
  `LoadPaletteColors` walks the entries and the aliased slots leak into the background; when a
  known palette is applied the same writes are invisible.
- `level_params[level<<1]` holds the exchange count (`game_apop1.c:206`): levels 0/1/2 = 2,
  3 = 0, 4 = 3, 5 = 4, 8 = 8 …  So level 1 *does* have two exchanges and is a valid test
  level; the earlier "A does nothing on level 1" run was a synthetic key that GSplus never
  delivered to the shim, not an `exchange==0` level.  Driving the trigger from inside the game
  (`i|=PAD_A; exchange=5;`) always reproduces the flash.

### Follow-up: the flash must not repaint the ego either

- The first fix flashed by switching the OAM palette bits (`|1` ↔ `|2`).  On screen that paints
  the ego with the **next** sprite palette — measured colours for the ego sprite:
  palette 0 → head `255,255,255` + body `119,187,255` (white head, pale-blue clothes = correct),
  the flash's alternate palette → head `255,119,85` + body `221,187,255` (**red head, white
  body**) — exactly what the user reported during an exchange.
- "Sometimes" was a second bug: `player_flash_cnt` is re-armed every frame of the swap, so the
  last evaluated value stayed in `player_atr`, leaving the ego on the wrong palette after the
  move until it walked again (the code only rewrites `player_atr` on movement/idle).
  Side-by-side evidence: `docs/screenshots/ego_flash_palette_compare.png` (left = the flash's
  alternate palette, red head / white body; right = the correct white head / blue clothes).
- **Final fix**: the flash is now a *visibility blink* — `if(player_flash_cnt) player_flash_cnt--;`
  plus the ego draw condition `(!start_delay||(start_delay&8))&&(!player_flash_cnt||(frame_cnt&1))`.
  Both egos blink (they share the palette, as in the NES original), the palette bits never change,
  so the ego keeps white head / blue clothes for the whole move.  The 50-frame `DONE_NOLUCK`
  (drowning) flash does the same with the sprite-0 off-screen row (`0,255,0,0`).
- **Verified** with the same forced-exchange harness, 70 frames at 2.8 MHz: sea = 0 orange px;
  ego colours observed = white `255,255,255` only (plus frames where the ego is blinked off);
  `255,119,85` / `221,187,255` / `187,34,0` never appear.
- Sprite-palette cheat sheet (colours measured on the ego sprite itself): the ego's own palette
  is the only one that renders white head `255,255,255` + pale-blue body `119,187,255` (the
  normal look, confirmed on the shipped build at level start); the other three sprite palettes
  give red head `255,119,85` + pale body `221,187,255`, magenta `255,0,255`/green `34,153,0`, and
  dark-teal `0,68,68`/grey `187,187,187`.  Flash by blinking, never by moving the ego onto
  another sprite palette.

### Performance at 2.8 MHz — measured, not assumed

- Two instruments, both left in the tree but disabled:
  - `RENDER_VBL_COUNT equ 1` (Config.s) draws `renderVblTicks` at the top-left (SHR $2000);
    its colour was `#$FFFF` (palette 15, never written ⇒ invisible) and is now `#$0303`.
  - `SHOW_DEBUG_VARS equ 1` (Config.s) draws fps/input/dirty/full counters (masks fixed, below).
- At `g_limit_speed = 2` the VBL digit reads **1** every frame ⇒ a full render fits inside one
  VBL interval (< 46,666 cycles), i.e. no frame overrun.
- The FamiTone2 update (`crt0_silky.s` NMI continuation: `jsr FamiToneUpdate`) is driven by the
  VBL once per NES frame, independent of the C game loop ⇒ music ticks at 60 Hz exactly while
  renders stay inside one VBL interval.
- The sea animation toggles every 16 game frames; measured 0.24–0.26 s at 2.8 MHz ⇒ ≈60–62 game
  frames/s.
- **Conclusion**: the port is not CPU-bound at 2.8 MHz.  GSplus on this VM caps at
  `Eff MHz: 2.55`, so the earlier "16 MHz" sessions were also ~2.55 MHz effective — the 16 vs
  2.8 comparison was meaningless.  A remaining stutter on other machines is an audio-path or
  host-speed question, not the renderer.

### Build-system trap — `src/game/` is dead for this game

Merlin32 resolves `put` paths relative to the **link file's directory**
(`src/games/alterego`), so the engine really reads `src/games/alterego/game/{Config.s,Hooks.s,...}`
and `src/games/alterego/{ppu,rom,core}/*.s`.  `stageEngineFiles` in `nromBuild.js` writes
`src/game/*`, which this build never sees (proved by putting a deliberate syntax error there:
the build still succeeded).  Behaviour changes must go into `src/games/alterego/game/Config.s`
and `src/games/alterego/{ppu,rom}/*.s`; the `src/game/*` and `src/ppu/*` copies are kept in sync
for source consistency only.

### Files touched

- `src/games/alterego/game_apop1.c` — flash fix (exchange + `DONE_NOLUCK`), comments explain the
  slot aliasing.
- `src/games/alterego/ppu/ppu.s` + `src/ppu/ppu.s` — `bne as_bitmap_clip` (145 bytes, over the
  127-byte limit once `SHOW_DEBUG_VARS` is on) replaced with `beq *+5` / `brl`.
- `src/games/alterego/ppu/ppu_frame.s` + `src/ppu/ppu_frame.s` — `_ShowDebugInfo` masks from
  palette-15 `$FFFF` to `$3333/$2222/$1111` (per-byte nibble masks leave digits striped).
- `src/rom/scaffold.s` + `src/games/alterego/rom/scaffold.s` — `RENDER_VBL_COUNT` digit colour
  `$FFFF` → `$0303`.
- `prg.bin` 32,768 B, SHA256 `C4CB044597B065F39E3435EF60869A6653ED388287B557B3087EFDB0C3AAD84D`
  (byte-reproducible);
  `AlterEgoGS` 313,213 B; `emu/AlterEgo.2mg` repacked
  (SHA256 `A3861EC1E71EECD272E086D25F5F3F0DFED84D38797ACD2491150343DB158C7C`, 10,485,824 B).
  The app/2mg are **not** byte-reproducible across rebuilds even with an identical `prg.bin`
  (the Merlin build embeds build-time data), so compare `prg.bin`, not the image hash.
  Verified booting at `Limit: 2.8Mhz` into level 1 (`docs/screenshots/level1_28mhz.png`).

## 2026-10-30c — credits screen: tighter rows, IIgs credit, 6 s hold

The credits screen is a compressed nametable, not a text block, so "just edit the lines" means
regenerating the array.  Everything below was measured or derived, not guessed.

### How `credits[]` works

- `credits_screen()` does `unrle_vram(credits,0x2000)` — the array is RLE VRAM that unpacks to
  **1024 bytes = 960 nametable bytes (32x30) + the 64-byte attribute table** (`$23C0..$23FF`), so one
  array carries both the glyphs and the colours.
- RLE format: `data[0]` is the tag (`$01`); a literal byte is stored as-is, and `tag,count` repeats
  the previous byte `count` **more** times.  The count is one byte, so a run longer than 256 must be
  emitted as several `tag,min(rest,255)` chunks — a naive encoder silently drops the tail and still
  looks plausible (the round-trip check in the generator catches it).
- Glyph codes (read out of the existing data): `A..P` = `$80..$8F`, `R..V` = `$6B..$6F`, `X` =
  `$7B`, `Y` = `$7C`, `Z` = `$7D`, `0..9` = `$F0..$F9`, space `$00`, `"` = `$FC`/`$FD`
  (opening/closing), and the copyright sign is the two cells `$7E,$7F`.
  Generator: `scripts/gen-credits.py`.
- Colour constraint: an NES attribute quadrant is 2 tiles tall and 2 wide, so rows 4k,4k+1 share one
  palette and 4k+2,4k+3 the next — two vertically adjacent single-height text rows **cannot** have
  different colours.  Leaving exactly **one** blank row between lines puts every line in its own
  quadrant, which is how the original screen alternated colours.  Measured palette ids: **3 = blue**,
  **1 = red with a yellow highlight**, **2 = deeper red/salmon without the highlight** (the original
  used 2 for `ALEX SHABANOV` — keep it).
- A false start is worth remembering: compacting the block to ten consecutive rows (no blank rows at
  all) fits and looks tidy in a screenshot, but it forces the colours to group in pairs and leaves a
  big empty area at the bottom — rejected by the user.  Keep one blank row.

### Final layout (all rows at text column 3)

| row | palette | text |
|---|---|---|
| 7  | 3 blue | `ORIGINAL ZX SPECTRUM GAME` |
| 9  | 1 red  | `(c) 2011 DENIS GRATCHEV` |
| 11 | 3 blue | `NES CONVERSION BY` |
| 13 | 1 red  | `SHIRU` |
| 15 | 3 blue | `NES MUSIC BY` |
| 17 | 1 red  | `RICHARD "KULOR" ARMIJO` |
| 19 | 3 blue | `HACKED BY` |
| 21 | 2 red  | `ALEX SHABANOV` |
| 23 | 3 blue | `APPLE IIGS VERSION BY` |
| 25 | 2 red  | `ANOMIXER 2026` |

- The block keeps the original first row (7) and bottom row (25) and the original one-blank-row
  rhythm; the two 3-row gaps before `NES CONVERSION BY` / `NES MUSIC BY` are gone (those headers
  moved up by 2 and 4 rows), which frees exactly the space for the two IIgs lines under
  `ALEX SHABANOV`.  `scroll(0,8)` is unchanged.
- Holding time: `credits_screen()` used `j=150` frames (2.5 s).  `j` is **`unsigned char`**
  (`game_apop1.c:376`), so writing `j=360` silently wraps to 104 — use a local `unsigned int hold`
  instead.  Now 360 frames = **6 s**, measured on the repacked image (fully drawn 6.03 s; harness
  `tmp/bench/timcred5.ps1 <out> rel28.kegs`).  START still skips the screen.
- Automation trap: `tmp/bench/rep28.kegs` boots **`AEBench.2mg`**, `rel28.kegs` boots
  `emu/AlterEgo.2mg`.  A stale bench image silently invalidates timing checks — repack
  `AEBench.2mg` before capturing, or time the release image directly.
- Evidence: `docs/screenshots/credits_iigs_version.png` (captured at `Limit: 2.8Mhz`).

## 2026-10-30 — sound test: Tab toggles back, spacing, yellow sprite digits

### What was done

- **A second Tab now closes the sound test.**  The in-loop `PAD_START` break fell through to the
  game-start path; the loop now sets `back_to_title` on `PAD_SELECT` and the close path clears the
  readout (`oam_clear`), restores `MUSIC ON/OFF` and `START LEVEL` with `title_draw_menu()` /
  `title_draw_level()`, restarts the title music unless muted, and `goto title_menu_again` (a label
  added at the top of the title menu loop) so the menu resumes instead of fading out.
- **Row 23 layout** (columns): the `MUSIC ON` label keeps its normal column 10 (`MUSIC ON` spans
  10–17, `MUSIC OFF` 10–18), so `ON` is followed by **two blank columns** and `OFF` by **one** — the
  row can never read `OFFSFX`.  `SFX` sits at 20–22, `BGM` at 26–28, and each value is glued to its
  label (`SFX00`, `BGM00`) with one blank column between the two fields.
- **The counter digits are OAM sprites**, not background text, exactly as in the original NES build:
  tiles `$F0–$F9` (the sprite-table copy of the digit glyphs) at columns 23–24 and 29–30.  Background
  attributes are 16×16 blocks, so background digits could only be recoloured together with the
  neighbouring `X` and blank cells; sprites leave every other cell untouched.
  OAM y is **175**: row 23 starts at scanline 184, the title scrolls `y=8` (the background moves up a
  tile, sprites do not), and the sprite renderer puts the first sprite line at `y+1`.
- **Selection colour**: the selected pair uses sprite palette 1, the other pair palette 2.
  `src/games/alterego/palettes/title.txt` sprite rows are now
  `SP1: $0F $01 $27 $38` (body `$38` = the logo's pale yellow, outline `$01` like the menu text) and
  `SP2: $0F $01 $11 $21` (identical entries to BG0, so the unselected digits match `MUSIC`/`SFX`
  exactly).  `SP0` (the `▶` cursor) and `SP3` are unchanged, and all BG rows are untouched — no other
  colour on the title screen changes.  `node build.js` regenerates `palettes.s`, `pal_defs.s` and
  `pal_transitions.s` from these files.
- `title_draw_sound_values()` is called once per frame in the sound-test loop (the NES original
  redraws its sprites every frame too), so the yellow follows Left/Right as well as value changes;
  the `oldpx`/`oldpy` bookkeeping is gone.

### Fix — the game's palette no longer stays on the title screen (the yellow digits turned red)

- **Symptom:** play a level, EXIT GAME back to the title, press Tab: the `SFX00`/`BGM00` digits came
  back in red/orange instead of yellow/light blue, and the menu text was a paler blue.
- **Cause:** the engine identifies a NES palette by the colours it holds (`PAL_*_MATCH`) and switches
  the slot layouts with it (`ApplyPaletteChange` → `DetectNESPalette` → `UpdatePalette`).
  `fade_screen_in(palTitleBG)` uploads its single 16-byte argument to **both** the background and the
  sprite palettes, so on the title the run-time sprite palettes are the four BG rows of `palTitleBG`
  (`$0F $01 $11 $21`, `$0F $16 $27 $38`, `$0F $06 $16 $26`, `$0F $11 $21 $31`).  `title.txt`'s SP
  rows were a copy of `palSprites`, so `PAL_TITLE_MATCH` could not match the title once another
  palette had been detected: `palCurrent` stayed on the level palette and the title was drawn through
  the level's slot layout (pale text, red digits).  At start-up it looked right only because
  `SetDefaultPalette` installs the title layout without detection.
- **Fix:** `palettes.h` gains `palTitleSPR[16]` holding the same four sprite rows as `title.txt`, and
  `fade_title_in()` (`game_apop1.c`) fades BG to `palTitleBG` and the sprite palettes to
  `palTitleSPR`; `credits_screen()` and `title_screen()` call it instead of `fade_screen_in()`.  The
  title's run-time sprite palettes now equal `title.txt`, so detection succeeds after a level and the
  digits keep palette 1 (yellow) / palette 2 (menu blue).
- **Do not "fix" this by making the SP rows equal the BG rows** (that was the first attempt): the
  palette generator rejects it (`title: the slot that BG3[3] is shown in is never loaded` — BG3[3]
  is `$31~$21`, shown in `$21`'s slot, and duplicating BG3 in SP3 makes the layout assign `$31` a
  slot no cell loads), and it would also give the `▶` cursor the BG0 colours instead of its grey
  `SP0: $0F $0C $10 $30`.  The separate sprite palette array is what keeps both.

### Fix — `_pad_poll` accepts X/Z however the keyboard reports them

- The shim already took both cases (`$58`/`$78`, `$5A`/`$7A`), plus the Ctrl-X/Z codes
  (`$18`/`$1A`) and the raw ADB keycodes (`$07`/`$06`), and both cases were verified through GSplus
  (`x x` / `z z` move the title cursor, `r2_*`, `t1_*` with 5 ms taps).  A user still reported that
  X/Z needed Caps Lock everywhere; that is the symptom of only the upper-case code being recognised,
  so the top bits a keyboard/ROM/emulator puts into `$C000` (case bit 5, strobe bit 7, some set
  bit 6) must not matter.
- `_pad_poll` now ends the key chain with `and #$1F` and compares `$18` (X) / `$1A` (Z), so any
  encoding whose low five bits are the letter works.  No other key collides: Tab `$09`, Return
  `$0D`/`$24`, Space `$20`, `P` `$50`/`$70`, the arrows `$08`/`$0A`/`$0B`/`$15` all keep distinct
  low five bits (the side effect is that `8` also reads as X's low bits and `:`/`;`+Shift as Z's).
  `neslib_silky.s` is assembled with `ca65 --cpu 65816` and the object is linked from
  `build/silky/tmp_verify/neslib_new.o` — **rebuild that object whenever the shim changes**, or the
  shipped PRG keeps the old one.
- Verified in the rebuilt image (`k3_*` in `iigs/tmp/variant_test/`): lower-case `x`, lower-case `z`
  and `8` (low-five-bit X) each move the title cursor one line, and the sound test after a level
  round trip still shows `SFX00` yellow / `BGM00` blue.

### Sound test: Space auditions the selection

- The user's keyboard still delivers X/Z only with Caps Lock on, so the sound test had no key that
  both works everywhere and plays.  **Space** is the NES A button (the same bit as Z), which made it
  "stop the BGM"; the shim now also exports `_pad_space` (a `BSS` byte set to 1 by `_pad_poll` only
  when the key being read is Space, reset to 0 at the start of every poll), so `game_apop1.c` can tell
  the two apart: **Z** keeps `music_stop()`, **Space** (like X) auditions `sfx_play(px,0)` /
  `music_play(musicData[py])`.  Left/Right select the field, Up/Down the value, Space plays, Tab
  closes — the sound test needs no X/Z.
- Watch the branch range: the new `lda #$00 / sta _pad_space` prologue pushed the `beq @no_key` after
  `lda $E0C010` past ±128, so it is now `bne @k0` + `jmp @no_key`.
- Verified (`sp_*` in `iigs/tmp/variant_test/`): Tab → sound test, Space ×2 (SFX00), Up Up → `SFX02`
  + Space, Right + Up → `BGM01` yellow + Space, Tab → title, Tab → sound test again.  The loop keeps
  redrawing throughout (`SFX02`/`BGM01` are on screen after the Space presses).  The generated
  `game_apop1.s` shows the branch: `and #$02 / bne play`, then `and #$01 / jeq skip`, then
  `lda _pad_space / jeq skip` — B (X) or Space+A plays while A alone (Z) stops.

### Open issue — X/Z still need Caps Lock on the user's machine (not reproducible here)

- Reported three times: on the user's machine `x`/`X` and `z`/`Z` do nothing until Caps Lock is
  pressed once, in every screen (title, in game, pause menu, sound test).  Not reproducible with this
  image in GSplus: `x x`/`z z` (lower case, no Caps Lock, 5 ms and 60 ms taps) move the title cursor,
  `_pad_poll` accepts `$58`/`$78`/`$18`/`$07` and `$5A`/`$7A`/`$1A`/`$06` **and** now matches the low
  five bits (`$18`/`$1A`), which covers any case/strobe/modifier bit pattern.  So the byte reaching
  `$C000` on that machine is not a variant of the ASCII/ADB code we know, or the emulator's keyboard
  layer swallows the letter keys — it is **not** the game logic as far as this port can tell.
- If it comes back, the next diagnostic is a throw-away build that draws `$C000 & $7F` as two hex
  digits on the title screen and compares a Caps Lock-off `x` with a Caps Lock-on `x`; that settles
  keyboard layer vs. game layer in one press.  The sound test no longer depends on X/Z (Space plays),
  which was the user's workaround.

### Verified (GSplus captures in `iigs/tmp/variant_test/`)

- `tabtoggle_*`: title → Tab → `MUSIC ON  SFX00 BGM00` → Tab → menu, cursor back on START GAME,
  title music resumed.
- `sel_*`: the `MUSIC OFF` variant reads `MUSIC OFF  SFX00` (one blank column, never `OFFSFX`);
  Right moves the yellow from `SFX00` to `BGM00`; Up changes the selected value to `03` while it
  stays yellow; Tab returns to the menu with `MUSIC OFF` preserved.
- `start_*`: Return in the sound test still starts level 1 (`HELLO WORLD`).
- `r2_*`: title → `x x` (lower-case x, no Caps Lock) moves the cursor START GAME → START LEVEL →
  MUSIC, `z z` moves it back; Tab → sound test → Right selects BGM; Return starts a level, pause →
  Down Down → Return (EXIT GAME) → title → Tab: `SFX00` yellow, `BGM00` light blue, and the title
  before/after the round trip has an identical colour histogram (`cmpimg.py`, 804 differing pixels =
  cursor/animated art only).  So both key cases reach `_pad_poll` and the title palette survives a
  level.
- Automation note: GSplus only sees the PC arrow keys when they are sent with
  `KEYEVENTF_EXTENDEDKEY` (`keybd_event(vk, scan, 1, 0)`); without the flag only Tab/Return reach
  the game.

### Current artifacts (updated)

| Item | Value |
|---|---|
| Image | `iigs/emu/AlterEgo.2mg`, 10,485,824 bytes |
| Image SHA-256 | `927B87B50054E86F6CAE99B975BD10D5274D886C503512874BAF6D2E1C1683C3` |
| App | `iigs/src/games/alterego/AlterEgoGS`, 313,125 bytes |
| App SHA-256 | `50C6AF9E3817FFBD56395CEDD724638A3F9511F339AC8AB9F116094D19E40A39` |
| PRG SHA-256 | `99B84E1F6787324993E67F49B26599616C0D9B484B50FD8DAC0A7F08E327D800` (`prg.bin`, 32,768 bytes) |

## 2026-10-29 — silky-gs v0.0.2 and animated sea

### What was done

- Fetched silky-gs tag **`v0.0.2` (`0c341d2`)** and merged its engine changes into `iigs/src`:
  `apu/apu.s`, `core/CoreImpl.s`, `core/Defs.s`, `core/Graphics.s`, `core/blitter/JoyProbes.s`,
  `misc/io.s`, `rom/rom_config.s`, `rom/rom_config_setup.s`, `rom/rom_exec.s`, `rom/rom_input.s`,
  `rom/rom_kbd_basic.s`, the new `rom/rom_kbd_macs.s`, and `runtime/head.txt` / `runtime/code.txt`.
- Preserved the port's own changes: `rom_exec.s` keeps `yieldFrame` and the `switchTask` `jmpl`
  bank fix; `core/Defs.s` keeps `YOffsetDyn=100` / `LayoutActiveDyn=102`; `scaffold.s` keeps its
  startup border diagnostics and `Fail` loop, plus the v0.0.2 `KBD_*` guards, `engineVideoOn` clear
  and APU render counter.
- `Main.s` now expands `rom_kbd_macs.s`; J13/ADB are disabled in `runtime/code.txt`, matching
  v0.0.2's BASIC-only default.  The config screen now opens with Shift-/ in the automated GSplus
  test and the engine suspends interrupts while it is open.
- Restored the sea animation without the 12 fps full-screen CHR toggle:
  - `chr.bin` page-0 tiles `$E0–$E3` contain the page-1 water art; `game_add_background` preserves
    the low two bits of `TILE_WATER`, and the every-16-frames pass rewrites only the water
    nametable cells with `vram_adr`/`vram_put`.
  - The water tiles deliberately stop before `$E4`: that tile is the HUD's `×` glyph (the stats
    meta-sprite and the `×5`/`×2` counters).  An earlier `$E1–$E4` layout overwrote it and made the
    top-left counters unreadable; moving the four wave variants to `$E0–$E3` fixed the HUD while
    keeping the sea animation.
  - The map scan uses a pointer (`mp = map; spr = *mp++`) because the generated 6502 indexing did
    not carry across a 256-byte page boundary.
- Palette layouts for game 1–5, GAME OVER and WELL DONE were regenerated; gameplay now has a
  blue-clothed player, green wall plants and blue/cyan water (no red sea line).
- **START LEVEL now accepts 0**, the hidden Cow Level.  The original NES trigger was Select+Start,
  but this port uses Select (Tab) for the sound test, so 0 is selected with Left/Right on the
  START LEVEL row.  The initial/default value remains 1, and START GAME still forces level 1.
- **X/Z input hardened**: the port previously had separate upper/lowercase comparisons but the
  user still had to tap Caps Lock before each X/Z.  `_pad_poll` now accepts `X`/`x`, `Z`/`z`,
  Ctrl-X/Ctrl-Z (`$18`/`$1A`) and the raw ADB Z/X codes (`$06`/`$07`); Caps Lock is never required.
  `ca65 --cpu 65816` is required when reassembling `neslib_silky.s` because it contains `phk`/`plb`.

### Verified

- New build boots from `emu/AlterEgo.2mg`; the title has the correct ALTER EGO logo colours, and
  Return on START GAME starts level 1; Return on START LEVEL with `00` starts the Cow Level.
- Shift-/ opens the control panel; the v0.0.2 interrupt suspend/resume path is active.
- Water animation frames differ at the 16-frame cadence and repeat with the expected period.
- HUD counters verified after the CHR fix: `shot_hudfix_a.png` shows `×5` and `×2` beside the
  player/ego icons, and the sea still animates (`shot_hudfix_a/b/c.png` differ in the water rows).
- Cow Level verified from a level-0 build: `shot_cow0_2cow.png` shows the distinct **COW LEVEL**
  banner and map, while normal builds still begin at level 1 (`shot_finalcheck_a.png`).
- X/Z case/repeat check on the new build: repeated X without Caps Lock moved the cursor
  `START LEVEL 01` → `MUSIC ON` → `SOUND ON`; Caps Lock followed by two X presses also worked
  (`shot_caps_1x.png`, `shot_caps_3x.png`, `shot_caps_6capsxx.png`).  The sound-test pass produced
  `SFX 00 BGM 00`, `SFX 01 BGM 00`, `SFX 01 BGM 01`, and Return entered Level 1
  (`shot_keyfix_1sound.png` … `shot_keyfix_6game.png`).

### Artifacts at 2026-10-29 (superseded by the table above)

| Item | Value |
|---|---|
| Image | `iigs/emu/AlterEgo.2mg` |
| Image size | 10,485,824 bytes |
| Image SHA-256 | `359D8C446C97FA827DE056092C47A2A17D3304DFC9841367340C01487F829A16` |
| App | `iigs/src/games/alterego/AlterEgoGS`, 312,895 bytes |
| App SHA-256 | `539383CD0D7ED2E7445DC185C65E1D623CBEA32105ACF06063DCD2B98E738DB7` |
| PRG input | `iigs/src/games/alterego/prg.bin`, exactly 32,768 bytes (E0 water, Cow menu, FamiTone build, X/Z aliases) |
| PRG SHA-256 | `007DD13EB35795A74C35617763D202B4430DA4D39AD7580BFE3542C2D2D656BB` |
| CHR SHA-256 | `7656616C52D4ACC34C745CAFB99B664CD49D4E4F4DBBCE7ED58ECA03EABCB1C0` |
| GSplus config | `iigs/emu/gsplus-alterego.kegs` |

## 2026-10-27 — snapshot and branch `test/gs`

### What was done

- Created branch **`test/gs`** from `master` in `C:\dev\alter-ego`.
- Copied the working `C:\dev\silky-gs` tree (the port actually used for the current image) into
  **`iigs/`** in this repository, preserving the silky-gs-relative paths so the build scripts still
  resolve:
  - `iigs/src/`, `iigs/scripts/`, `iigs/macros/`, `iigs/tests/`, `iigs/plans/`, `iigs/docs/`
  - the generated Merlin32 listing/map files (`*_Output.txt`, `*_Symbols.txt`) were **not** copied;
    they are regenerated by the build and are gitignored.
  - `iigs/emu/AlterEgo.2mg` and `iigs/emu/gsplus-alterego.kegs` are the current review image
    and its GSplus config.
  - a few reference captures are in `iigs/docs/screenshots/`.
- Fixed the copied GSplus config so `s7d1` points at
  `C:\dev\alter-ego\iigs\emu\AlterEgo.2mg` rather than the old `C:\dev\silky-gs` path.
- Updated `iigs/package.json` `config.cadius` to the Cadius in this environment
  (`C:\dev\cadius.exe`).

### Previous committed image (2026-10-27, superseded by the table above)

| Item | Value |
|---|---|
| Image | `iigs/emu/AlterEgo.2mg` |
| Size | 10,485,824 bytes |
| SHA-256 | `8A10009113D6A5FE87B350488B895E2E9ACF30368C56AE17BD800885F0F03E3D` |
| App | `iigs/src/games/alterego/AlterEgoGS`, 268,275 bytes |
| App SHA-256 | `57B7483BF9140F57E4391B66EDED7C516824CB0A4560FF0DFC94615790672606` |
| PRG input | `iigs/src/games/alterego/prg.bin`, exactly 32,768 bytes (audio-enabled FamiTone build) |
| SHA-256 (PRG) | `28328DB5D17093BC5A40A30007CE811A3EA2EE2D0683CF95BDF667E1F9956855` |
| GSplus config | `iigs/emu/gsplus-alterego.kegs` |

Current screen evidence: `iigs/docs/screenshots/shot_final_aligned_game.png` (gameplay),
`shot_final_credits.png` (centred credits), `shot_final_title.png` (centred title with PRESS START)
and `shot_config_menu.png` (runtime options menu).

### Current visual/audio state

- Boots; Return at the title starts level 0.  Music and SFX are enabled and audible in GSplus
  (host loopback capture RMS 3532, peak 27610).
- Final layout: one continuous gameplay band, SHR lines 0–199 sourced from NES rows 16–215
  (`Config.s`: `y_offset equ 16`).  The HUD stats, outer frame and playfield share that band; there
  is no separate HUD source range and no blank strip below the frame (it ends flush on SHR line 199).
- The title/credits keep their own full-screen treatment with `YOffsetAbs = 31`, lifting the logo and
  text into the 200-line SHR area.  The title path calls `NES_SetScroll` with the latched
  `_ppuscroll_x/_ppuscroll_y` before `PPU_DrawScreenRange`, so the 16-frame nametable toggle that
  blinks **PRESS START** is preserved.
- Dirty-grid rendering is enabled (`ENABLE_DIRTY_RENDERING=1`, `GRID_COMPACT_SPRITES=1`).  Background
  cells are emitted by the grid; the compact sprite mapping keeps OAM screen coordinates (stats,
  player/enemies, pause menu) aligned with the NES 16–215 band.  The C fallback full renderer uses the
  same `YOffsetAbs = 16`.
- `HELLO WORLD` and the man/ego counters are in the fixed top band; the playfield does not scroll.
  Player/enemy sprites and the pause menu are visible, and the player moves with input.
- Pause entry dims the palette and draws RESUME/RESTART as sprites; resuming restores the palette,
  clears the menu OAM and redraws the stats.  Up/Down selects, Return confirms.
- Audio root cause found and fixed: FamiTone's `$7E30` APU trampolines were actually assembled at
  `$7E2D`, and FamiTone is 8-bit code.  The table is now padded to `$7E30` and `crt0` sets `sep #$20`
  before the FamiTone init calls.  This eliminated the `Emulated state corrupt` crash.

### Runtime options and hidden inputs (2026-10-27)

- `iigs/src/games/alterego/Config.s` now sets **`NO_CONFIG equ 0`**.  The stock
  Audio/Input/Drivers/Credits panels are present; `CONFIG_VIDEO_MENU=0`,
  `CONFIG_GAME_MENU=0`, `CONFIG_INPUT_2P=0` and `JOYSTICK_SUPPORT=0` remain off.
- The menu is opened with **`?`**.  Before v0.0.2, `[System.Windows.Forms.SendKeys]::SendWait('?')`
  was the reliable automation path and synthetic Shift-`/` was not.  With the v0.0.2 input layer,
  explicit Shift down + `keybd_event` for `/` (VK 191 / scan 0x35) opens it consistently; use that
  for the current build.
- **Cow Level verified** by holding Tab and pressing Return at the title
  (`shot_cowlevel.png` locally; the level 0 layout is visibly different).
- **Sound Test** and the **B, Left, A, B, Left, A** level-skip sequence come from the
  original `src/game.c` title logic (`py=1` / `code_str`); they were **not captured**
  through GSplus because the host Command/Option injection was unreliable.  The README
  documents the logical keys and the GSplus swap caveat instead of claiming an
  emulator capture.
- Menu Return exits back to the game without changing the rendering layout; the
  gameplay capture after Return is unchanged.

### Rebuilding `prg.bin` from the C sources (2026-10-30 recipe, tree imported 2026-11-01)

`iigs/src/games/alterego/game_apop1.c` and `prg.bin` are the two files in this repository that are
*built elsewhere*: the C/PRG staging tree is **`iigs/prg-src`** (imported on 2026-11-01 from
`C:\dev\alter-ego\build\silky` in the archived upstream tree — see `iigs/prg-src/README.md`), and
`palettes.h` (the 16-byte `palTitleBG` / `palTitleSPR` / `palSprites` / `palWellDone` arrays) lives in
`iigs/prg-src/work`.  `game_apop1.c` is reference-only in the repo; it is compiled with `-I .` from
that work directory.

The link below was **verified to reproduce the shipped `prg.bin` byte for byte** (32,768 bytes,
SHA256 `C4CB0445…`) on 2026-11-01:

```powershell
# 1. relink the 32,768-byte PRG from the objects kept in prg-src
cd C:\dev\alter-ego\iigs\prg-src
& C:\dev\cc65\bin\ld65.exe -C nes_silky.cfg -o prg.bin `
    objects\crt0_silky.o objects\neslib_new.o objects\game_fixed.o objects\audio_silky.o `
    C:\dev\cc65\lib\nes.lib

# 2. put it where the Merlin build picks it up, then rebuild the app and repackage
Copy-Item prg.bin C:\dev\alter-ego\iigs\src\games\alterego\prg.bin -Force
cd C:\dev\alter-ego\iigs\src\games\alterego
node build.js
```

To rebuild the objects as well (the 2026-10-30 path): the keyboard/palette/OAM shim is 65816
(`phk`/`plb`), so reassemble it with `ca65 --cpu 65816 neslib_silky.s -o objects\neslib_new.o` —
the linker does not notice the `.s` on its own; then `cc65 -Os -I . -I ..` + `ca65 --cpu 6502` on
`work/game_apop1.c` from `iigs/prg-src/work`.

`prg.bin` must stay exactly 32,768 bytes; `ld65` prints one harmless `sp` deprecation assertion and
cc65 prints three pointer-signedness warnings from `game_apop1.c` on every build.  Keep
`iigs/prg-src/neslib_silky.s` and `iigs/src/games/alterego/neslib_silky.s` byte-identical (copy after
editing), and the same for `game_apop1.c`.

### Build (verified in the snapshot)

```powershell
cd C:\dev\alter-ego\iigs\src\games\alterego
node build.js
```

The verified output is:

```
MAIN         23732 -> 22319 bytes
STKDP        6470 -> 65 bytes
ENGINE       31638 -> 26789 bytes
PPU1         61787 -> 58426 bytes
PPU2         61787 -> 58427 bytes
CHRDATA      65606 -> 62730 bytes
AEROM        65828 -> 31766 bytes
PPURAM       16454 -> 7753 bytes
AlterEgoGS: 333302 -> 268275 bytes
```

`package.json` `config.merlin32` is `C:\dev\Merlin32.exe`; `config.cadius` is `C:\dev\cadius.exe`.
`PROJECT_ROOT` is inferred from `scripts/lib/nromBuild.js`, so the build must run from inside the
`iigs/` tree.

### Repackage image

```powershell
cd C:\dev\alter-ego\iigs
New-Item -ItemType Directory tmp\repackage -Force | Out-Null
Copy-Item build\AlterEgoGS 'tmp\repackage\AlterEgoGS.S16#B3DB03' -Force
& C:\dev\cadius.exe REPLACEFILE build\AlterEgo.2mg /ALTEREGO 'tmp\repackage\AlterEgoGS.S16#B3DB03'
```

Cadius takes the ProDOS type from the `#B3DB03` suffix; staging the file as plain `AlterEgoGS.S16`
replaces the file as `UNK $0000` and the image will not launch correctly.  Use `REPLACEFILE` (not
`ADDFILE`) to replace the existing `/ALTEREGO/AlterEgoGS.S16`, and confirm with `CATALOG` that the
entry reads `S16 $DB03`.

### Run / screenshot

```powershell
Start-Process C:\dev\emu\GSplus\gsplus.exe `
  -ArgumentList '-cfg', (Resolve-Path C:\dev\alter-ego\iigs\emu\gsplus-alterego.kegs)
```

Wait about **24 seconds** at 16 MHz (or **2–3 minutes** with `g_limit_speed = 2`, the factory
2.8 MHz), focus the GSplus window, then send **Return once** at the title. Earlier Returns are lost.  For the options menu, focus the window and send `?` with
`SendKeys`; see the runtime-options section above. Screenshot with the GSplus `MainWindowHandle`
and `CopyFromScreen`; raise the window to topmost before capture if the DSH GUI overlaps it.

## Hard constraints found in this port

### `y_offset`, dirty grid and sprite alignment

The working configuration is:

- `iigs/src/games/alterego/Config.s`: `y_offset equ 16`, `GRID_COMPACT_SPRITES equ 1`
- `iigs/src/games/alterego/ppu/ppu_grid_quads.s` (the game-local copy actually built): the
  `gqInitTables` Y loop skips the `sbc #y_offset` when `GRID_COMPACT_SPRITES=1`
- `Main.s` gameplay: `YOffsetAbs=16`, return C=0 so the grid draws; no `NES_SetScroll` and no
  `StartY=16`

Two traps, both seen in this port:

1. If the custom renderer returns C=0, `RenderScreen` calls `_SetScroll` again from the latched
   `_ppuscroll` *after* the custom code.  Setting `StartY=16` inside the custom renderer is therefore
   discarded; the source offset must be the configured `y_offset`, not the runtime start line.
2. The C side puts OAM in SHR screen coordinates.  With `y_offset=16`, the grid must not subtract 16
   again for sprites; without the compact flag the menu/stats and player sprites move or go negative
   and GSplus reports `Code: RED Emulated state corrupt`.  Keep `GRID_COMPACT_SPRITES=1` in the
   built copy and verify the game-local `ppu_grid_quads.s`, not just `src/ppu/`.

The 2.8 MHz target and the 16 MHz build use the same single gameplay band; the title/credits are the
only screens drawn with `YOffsetAbs=31`.

### Conditional blitter scrolling is unsafe

Adding a `cmp #HUD_FIXED_LINES` / conditional `add_y_offset` in
`iigs/src/core/blitter/BlitterLite.s` caused GSplus **`Emulated state corrupt`**, a black screen or a
System 6 reboot. Both macro-local and inline variants failed. The three `add_y_offset` sites are back
to unconditional. Do not retry the same per-line conditional in the blitter without a different
strategy.

### `POST_RENDER` direct SHR writes

A `POST_RENDER` hook that wrote a bottom border directly into `$E1/2000 + row*160` also led to a
corrupt boot (likely a bad/stale `ScreenY1`/address path during the title). That code was removed.
If a border/overlay is needed later, it must be gated on a valid game screen and verified in GSplus.

### Audio

The current image is built from the **audio-enabled FamiTone PRG** (`prg.bin`, SHA-256
`C4CB0445…`). The earlier `Emulated state corrupt` crash was fixed by padding the APU trampoline
table to `$7E30` and keeping the FamiTone init in 8-bit mode (`sep #$20`). A host loopback capture
of GSplus gameplay measured RMS 3532 / peak 27610, so the current build is audible; do not replace
`prg.bin` with the old audio-off baseline.

The port can pause the music from the engine side without calling into the ROM: FamiTone2 keeps its
song speed (and its pause flag) in bit 7 of NES RAM `$0101`, i.e. `ROMBase+$0101` in the AEROM bank.
Write it **one byte wide** (`sep #$20` / `ldal` / `stal` / `rep #$20`): a 16-bit `stal` also writes
`$0102` (a FamiTone counter), and a 16-bit `and #$7F` on the unpause path zeroes that byte — the
symptom is the title screen drawn but the game ignoring every key (see the 2026-10-31 entry).

### Emulator / packaging gotchas

- Launch GSplus with `-cfg <file>`, **not** `-kegs`.
- `cadius` uses `REPLACEFILE`; `LIST` is invalid (`CATALOG` is the listing command).
- Do not move/resize the GSplus window; capture the existing window rectangle.
- `prg.bin` must be exactly 32,768 bytes; `__ROM0_LAST__` is `00F6B3`.

## Repository boundaries

- `iigs/` is the self-contained silky-gs snapshot for this port. Edit
  `iigs/src/games/alterego/...` for game changes; engine edits go under `iigs/src/core`,
  `iigs/src/ppu`, `iigs/src/rom`.
- `iigs/src/game/` is build scratch created by `stageEngineFiles`; it is gitignored. Never edit the
  staged copies, edit the game's own `Config.s`/`Hooks.s`/`EngineExt.s`.
- Merlin32 listing/map files are regenerated; don't commit them.
- The original `//e` material in the repository root is archived; do not resume it unless the user
  explicitly reopens it.

## Push status

- **`master` is the only branch** on `origin` (`https://github.com/anomixer/alter-ego`).  The
  working branch **`test/gs`** was fast-forward merged into `master` on 2026-11-01 and then deleted
  locally and on `origin` — do further work directly on `master`.  No local backup branch is kept;
  the pre-squash branches were deleted once the squashed history was pushed.
- **History squashed twice on 2026-11-01.**  The day's work was first squashed into the port commit,
  then squashed again at the end of the day: all 13 commits of 2026-11-01 — the port, the move to
  `build/`, the archived `//e` import, the rename to `alter-ego` and the README work — are a
  **single commit on top of `fc19266`** (the VERA port).  **Every commit hash quoted in the dated
  entries below is a pre-squash label and no longer resolves on `master`**; keep them as labels only.
- Inside that single commit: the whole port plus the 2026-10-30/31 title-palette, X/Z, sound-test and
  level-start music-hold work, the `emu/AlterEgo.2mg` rename, `build/` as the deliverable
  directory, `iigs/prg-src/`, `docs/archive/apple2e/`, and the two-target README — see the entries at
  the top of this file and `CHANGES.md`.
- The VERA port at the repository root keeps its own release commit `fc19266`; `iigs/` is additive to
  it.
- The ~170 investigation captures in `iigs/docs/screenshots/` stay local: `iigs/.gitignore` ignores
  that directory and allowlists only the 20 reference images that are tracked (the ones cited by
  `README.md` / `AGENTS.md` plus the earlier committed evidence).  `credits.h` in
  `src/games/alterego/` is generated and tracked.  Do not add captures with `git add -A`.
  `build/AlterEgoOld.2mg` used to be listed here; it was deleted on 2026-11-01.

## Next steps

1. The sound test is finished: Tab opens it, a second Tab closes it, Space auditions the selection,
   Left/Right pick the field, Up/Down change the value, Return starts the game.
2. The level-start music hold is finished: LEVEL CLEAR keeps the music, the switch into the next
   level and the READY blink are silent, and the song starts with the player.  Keep the `$0101`
   access one byte wide if it is ever touched again.
3. The title palette is stable across a level round trip; keep `palettes/title.txt`'s SP rows and
   `palettes.h`'s `palTitleSPR` in sync — changing one alone re-breaks detection (symptom: the digits
   come back red/orange and the menu text goes pale after EXIT GAME).
4. Keep `prg.bin` a 32,768-byte, audio-enabled FamiTone build produced by the recipe above; never
   replace it with the historical audio-off baseline.
5. Open, not reproducible here: X/Z needing Caps Lock on the user's machine (see the section above);
   next action is the throw-away hex readout build if it is reopened.
6. Screenshot gap only: the user played the port from boot to the ending on 2026-11-01 and reported it
   normal, so levels 1–5, LEVEL CLEAR and the WELL DONE ending are exercised in practice; the
   repository still has no captures of GAME OVER, WELL DONE, LEVEL CLEAR or levels 2–5.  Capture them
   if they are ever needed as evidence — nothing about the port depends on it.
7. **Release published** (2026-11-04, tag `iigs-v0.0.2`) — supersedes this bullet's "deliberately
   unpublished" state of 2026-11-03 (user: 「先ready好, 不急著release」).  The GitHub release carries
   `build/AlterEgo.2mg` and `build/AlterEgo-full.2mg`; the `.po` is not an asset.  What anyone running
   it needs to know: boot at ≥ 7.1 MHz / 16 MHz; below that the port falls back to its 2.8 MHz cadence
   (about 30 fps, 2–3 minute boot).  See 2026-11-04e for the tag, assets and hashes.

## Provenance

The engine files under `iigs/` come from Lucas Scharenbroich's silky-gs
(`https://github.com/lscharen/iigs-game-engine`, Apache-2.0). The upstream README is preserved at
`iigs/docs/SILKY-GS-UPSTREAM-README.md`; the NES/Alter Ego game material keeps its original project
licensing. This branch is a port snapshot, not a relicensing of upstream.
