# Third-party notice — web/nes

## jsnes 2.1.0

- Upstream: https://github.com/bfirsh/jsnes
- License: **Apache-2.0** (declared in the upstream `package.json`)
- Vendored file: `vendor/jsnes.min.js`, taken from `https://unpkg.com/jsnes@2/dist/jsnes.min.js`
  (135,545 bytes).  It handles CPU/PPU/APU emulation, canvas rendering, WebAudio output, input
  mapping and frame pacing; this directory only adds the page and the ROM loader.

The ROM itself is **not** covered by this notice and is not distributed with the repository: it is
generated locally by `build-rom.mjs` into `build/`, which is gitignored.
