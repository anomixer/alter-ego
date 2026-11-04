// Cut the landing page's ALTER EGO mark out of the NES title screen.
//
//   node web/nes/make-logo.mjs [--frame N] [--out path] [--report]
//
// The title screen draws each word twice: a bright copy and a dimmer copy one
// tile row below it (ALTER's dim copy is the reddish band under the letters,
// EGO's is the blue band above them).  What the page wants is the letters
// only, one clean word each, in the colours the words are known by: ALTER
// orange/amber, EGO blue.  So the script takes the *bright* copy of each word
// (ALTER's background layer, EGO's sprite layer), drops the dim copy and the
// scattered stars, and recolours each word's shades onto the other word's
// ramp (dark -> dark, mid -> mid, light -> light), which is exactly the two
// ramps the title screen itself uses:
//
//   blue   0,25,188 / 0,180,247 / 136,237,248      (ALTER's letters, PRESS START)
//   orange 255,64,0 / 255,171,60 / 255,242,190     (EGO's letters)
//
// The title stacks the words (ALTER on top, EGO below it); the page shows them
// on one line, so each word keeps its columns and moves up to a shared top row.
// Black becomes alpha 0 so the mark sits on the page's #0b0b10.  The result is
// committed as web/assets/alter-ego-logo.png; re-run this if the title art
// changes.  See iigs/AGENTS.md, entry 2026-11-04i.

import { readFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { writePngRgba } from "./png.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const jsnes = require(join(here, "vendor", "jsnes.min.js"));

const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const FRAME = Number(opt("--frame", 420));
const OUT = opt("--out", join(here, "..", "assets", "alter-ego-logo.png"));
const REPORT = args.includes("--report");
const ROM = join(here, "build", "alterego.nes");

const SCREEN_W = 256;
const MIN_COMPONENT = 16; // the stars are 1-4 px; a letter stroke is far bigger

// The bright copy of each word.  ALTER is background tiles, so its box sits
// above the dim band; EGO is sprites, so its box sits below ALTER's band.
const WORDS = [
  {
    name: "ALTER",
    // columns 24..150, rows 56..95 (5 tile rows)
    box: { x0: 20, x1: 158, y0: 50, y1: 96 },
    isShade: (r, g, b) => b > r, // blue copy
    ramp: [
      [0, 25, 188],
      [0, 180, 247],
      [136, 237, 248],
    ],
    target: [
      [255, 64, 0],
      [255, 171, 60],
      [255, 242, 190],
    ],
  },
  {
    name: "EGO",
    // columns 161..230, rows 96..134 (5 tile rows)
    box: { x0: 158, x1: 236, y0: 96, y1: 140 },
    isShade: (r, g, b) => r > b, // orange copy
    ramp: [
      [255, 64, 0],
      [255, 171, 60],
      [255, 242, 190],
    ],
    target: [
      [0, 25, 188],
      [0, 180, 247],
      [136, 237, 248],
    ],
  },
];

// --- boot the ROM and take the title frame -------------------------------

let last = null;
const nes = new jsnes.NES({
  onFrame: (buffer) => {
    last = Int32Array.from(buffer);
  },
  onAudioSample: () => {},
  emulateSound: false,
});
nes.loadROM(readFileSync(ROM));
for (let f = 1; f <= FRAME; f++) nes.frame();
if (!last) throw new Error(`no frame ${FRAME}`);

const at = (x, y) => {
  const v = last[y * SCREEN_W + x];
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
};
const key = (r, g, b) => `${r},${g},${b}`;

// --- keep only letters: drop components smaller than a stroke ------------

const keepComponents = (mask, w, h) => {
  const seen = new Uint8Array(w * h);
  const out = new Uint8Array(w * h);
  const stack = [];
  let dropped = 0;
  for (let i = 0; i < w * h; i++) {
    if (!mask[i] || seen[i]) continue;
    const cells = [];
    stack.push(i);
    seen[i] = 1;
    while (stack.length) {
      const j = stack.pop();
      cells.push(j);
      const x = j % w;
      const y = (j - x) / w;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const nx = x + dx;
        const ny = y + dy;
        if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
        const k = ny * w + nx;
        if (mask[k] && !seen[k]) {
          seen[k] = 1;
          stack.push(k);
        }
      }
    }
    if (cells.length >= MIN_COMPONENT) for (const j of cells) out[j] = 1;
    else dropped += cells.length;
  }
  return { mask: out, dropped };
};

// --- collect each word's pixels, recoloured ------------------------------

const words = WORDS.map((word) => {
  const { x0, x1, y0, y1 } = word.box;
  const w = x1 - x0 + 1;
  const h = y1 - y0 + 1;

  const shades = new Set();
  const raw = new Uint8Array(w * h);
  for (let y = y0; y <= y1; y++) {
    for (let x = x0; x <= x1; x++) {
      const [r, g, b] = at(x, y);
      if (r + g + b === 0 || !word.isShade(r, g, b)) continue;
      raw[(y - y0) * w + (x - x0)] = 1;
      shades.add(key(r, g, b));
    }
  }

  // The title's own ramp, ordered dark -> light; anything unexpected in the
  // box (a star, a neighbour's pixel) is mapped onto the nearest one.
  const ramp = word.ramp.map((c) => c.join(","));
  const byLuma = (k) => k.split(",").reduce((sum, v) => sum + Number(v), 0);
  const ordered = [...shades].sort((a, b) => byLuma(a) - byLuma(b));
  const map = new Map();
  for (const shade of ordered) {
    let best = 0;
    let bestDist = Infinity;
    ramp.forEach((c, i) => {
      const d = Math.abs(byLuma(c) - byLuma(shade));
      if (d < bestDist) {
        bestDist = d;
        best = i;
      }
    });
    map.set(shade, word.target[best]);
  }

  const { mask, dropped } = keepComponents(raw, w, h);

  const pixels = [];
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (!mask[y * w + x]) continue;
      const absX = x0 + x;
      const absY = y0 + y;
      const [r, g, b] = at(absX, absY);
      const to = map.get(key(r, g, b));
      if (!to) continue;
      pixels.push([absX, absY, to]);
      if (absX < minX) minX = absX;
      if (absX > maxX) maxX = absX;
      if (absY < minY) minY = absY;
      if (absY > maxY) maxY = absY;
    }
  }

  if (REPORT) {
    console.log(
      `${word.name}: box x ${x0}..${x1} y ${y0}..${y1}, ` +
        `shades ${ordered.map((k) => `${k}->${map.get(k).join(",")}`).join(" ")}, ` +
        `kept ${pixels.length} px, dropped ${dropped} px of stars, ` +
        `bbox x ${minX}..${maxX} y ${minY}..${maxY}`,
    );
  }
  return { word, pixels, box: { minX, maxX, minY, maxY } };
});

// --- compose: one line, ALTER left and EGO right, crop to what is left ---

// The title stacks the words (ALTER on top, EGO below it).  The page wants them
// on one line, so every word keeps its columns and is moved up to the top row
// of the block: both words are five tile rows tall, so they share a baseline.
const top = Math.min(...words.map((w) => w.box.minY));
for (const w of words) w.dy = top - w.box.minY;

const minX = Math.min(...words.map((w) => w.box.minX));
const maxX = Math.max(...words.map((w) => w.box.maxX));
const minY = top;
const maxY = Math.max(...words.map((w) => w.box.maxY + w.dy));
const width = maxX - minX + 1;
const height = maxY - minY + 1;
const rgba = Buffer.alloc(width * height * 4); // alpha 0 everywhere

const opaque = new Set();
for (const { pixels, dy } of words) {
  for (const [x, y, [r, g, b]] of pixels) {
    const i = ((y + dy - minY) * width + (x - minX)) * 4;
    rgba[i] = r;
    rgba[i + 1] = g;
    rgba[i + 2] = b;
    rgba[i + 3] = 255;
    opaque.add((y + dy - minY) * width + (x - minX));
  }
}

mkdirSync(dirname(OUT), { recursive: true });
writePngRgba(OUT, width, height, rgba);
console.log(
  `${OUT}: ${width}x${height}, ${opaque.size} opaque px, ` +
    `x ${minX}..${maxX} y ${minY}..${maxY} (frame ${FRAME})` +
    (REPORT ? `, shifts ${words.map((w) => `${w.word.name} dy ${w.dy}`).join(", ")}` : ""),
);
