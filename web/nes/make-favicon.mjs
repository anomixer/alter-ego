// Draw the site favicon from the game's own player sprite.
//
//   node web/nes/make-favicon.mjs [--out-dir <dir>] [--report]
//
// The protagonist is the active ego: two stacked 8x8 sprite tiles, PLAYER_SPR_IDLE
// (0x90) and 0x90+0x10 (0xA0), drawn with OAM attribute 1, i.e. sprite palette 1
// (`src/game.c`: `player_atr=1`, `oam_spr(player_x1, player_y1-8, player_spr, ...)`).
// Sprite palette 1 is `{0x0F, 0x30, 0x21, 0x11}` (`palSprites` in
// `src/palettes.h`; the same list is `SP1:` in `iigs/src/games/alterego/palettes/
// game1.txt`), so the character is a white face with blue eyes and light-blue
// clothes — the blue-clothed protagonist the pages use as their mark.
//
// The tiles come straight from `src/tileset.chr` (the 8 KiB CHR-ROM image the NES
// build links), so this needs no ROM build; the colours come from the standard NES
// master palette as the ports use it (`iigs/src/rom/rom_color.s`,
// `NES_ColorPalette`), because the emulator's own palette table is shifted:
//
//   NES 0x30 -> $0FFF -> 255,255,255   face, hands, legs
//   NES 0x21 -> $07BF -> 119,187,255   clothes, outline
//   NES 0x11 -> $007E ->   0,119,238   eyes
//
// Black (colour 0) becomes alpha 0, the empty rows of the top tile are trimmed,
// and the sprite is centred at 1x in a 16x16 icon and 2x in a 32x32 one, so both
// sizes are pixel-exact instead of resampled.  The results are committed as
// web/assets/favicon-16.png and web/assets/favicon-32.png; re-run this if the
// player art changes.

import { readFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { writePngRgba } from "./png.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..");

const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const OUT_DIR = opt("--out-dir", join(here, "..", "assets"));
const REPORT = args.includes("--report");

// CHR-ROM tile data: 16 bytes per 8x8 tile.
const CHR = readFileSync(join(repoRoot, "src", "tileset.chr"));
const PLAYER_TOP = 0x90; // PLAYER_SPR_IDLE
const PLAYER_BOTTOM = PLAYER_TOP + 0x10; // the second half of the 8x16 metatile

// Sprite palette 1: NES colour -> RGB.  Colour 0 is transparent in an OAM sprite.
const PALETTE = {
  1: [255, 255, 255], // 0x30
  2: [119, 187, 255], // 0x21
  3: [0, 119, 238], // 0x11
};

function tilePixels(index) {
  const base = index * 16;
  const rows = [];
  for (let y = 0; y < 8; y++) {
    const low = CHR[base + y];
    const high = CHR[base + y + 8];
    const row = [];
    for (let x = 0; x < 8; x++) {
      // NES bitplanes are big-endian: bit 7 is the leftmost pixel.
      const bit = 7 - x;
      row.push(((low >> bit) & 1) | (((high >> bit) & 1) << 1));
    }
    rows.push(row);
  }
  return rows;
}

// 8x16 sprite, colour indices, top half above the bottom half.
const sprite = [...tilePixels(PLAYER_TOP), ...tilePixels(PLAYER_BOTTOM)];

// Trim fully transparent rows and columns (the idle tile leaves its top 3 rows empty).
const hasColour = (v) => v !== 0;
const firstRow = sprite.findIndex((row) => row.some(hasColour));
const lastRow = sprite.length - 1 - [...sprite].reverse().findIndex((row) => row.some(hasColour));
const visible = sprite.slice(firstRow, lastRow + 1);
const firstCol = Math.min(...visible.flatMap((row) => row.map((v, x) => (hasColour(v) ? x : 99))));
const lastCol = Math.max(...visible.flatMap((row) => row.map((v, x) => (hasColour(v) ? x : -1))));
const art = visible.map((row) => row.slice(firstCol, lastCol + 1));
const artW = art[0].length;
const artH = art.length;

function draw(size, scale) {
  const rgba = Buffer.alloc(size * size * 4); // alpha 0 everywhere
  const x0 = Math.floor((size - artW * scale) / 2);
  const y0 = Math.floor((size - artH * scale) / 2);
  let opaque = 0;
  for (let y = 0; y < artH; y++) {
    for (let x = 0; x < artW; x++) {
      const colour = PALETTE[art[y][x]];
      if (!colour) continue;
      for (let dy = 0; dy < scale; dy++) {
        for (let dx = 0; dx < scale; dx++) {
          const px = x0 + x * scale + dx;
          const py = y0 + y * scale + dy;
          if (px < 0 || py < 0 || px >= size || py >= size) continue;
          const i = (py * size + px) * 4;
          rgba[i] = colour[0];
          rgba[i + 1] = colour[1];
          rgba[i + 2] = colour[2];
          rgba[i + 3] = 255;
          opaque++;
        }
      }
    }
  }
  return { rgba, opaque, x0, y0 };
}

mkdirSync(OUT_DIR, { recursive: true });
for (const [size, scale] of [
  [16, 1],
  [32, 2],
]) {
  const { rgba, opaque, x0, y0 } = draw(size, scale);
  const file = join(OUT_DIR, `favicon-${size}.png`);
  writePngRgba(file, size, size, rgba);
  console.log(
    `${file}: ${size}x${size}, art ${artW * scale}x${artH * scale} at ${x0},${y0}` +
      ` (${opaque} opaque px, source tile 0x${PLAYER_TOP.toString(16)}/0x${PLAYER_BOTTOM.toString(16)})` +
      (REPORT ? `, trimmed rows ${firstRow}..${lastRow} cols ${firstCol}..${lastCol}` : ""),
  );
}
