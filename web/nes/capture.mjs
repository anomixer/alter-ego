// Headless jsnes run: boots a ROM, optionally presses Start, and writes PNG
// captures so "the title drew" can be checked by machine instead of by eye.
//
// Usage:
//   node capture.mjs --frames 900 --at 900 --out build/shots/title.png
//   node capture.mjs --frames 1500 --start-at 900 --at 1500 --out build/shots/level1.png
//
// --at takes a comma separated list of frame numbers; one PNG per entry.
// --rom defaults to build/alterego.nes (see build-rom.mjs).

import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { writePng, frameStats } from "./png.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const jsnes = require(join(here, "vendor", "jsnes.min.js"));

function arg(name, fallback) {
  const i = process.argv.indexOf("--" + name);
  return i >= 0 ? process.argv[i + 1] : fallback;
}

const romPath = resolve(arg("rom", join(here, "build", "alterego.nes")));
const totalFrames = Number(arg("frames", "900"));
const startAt = Number(arg("start-at", "-1"));
const outPath = arg("out", join(here, "build", "shots", "frame.png"));
const atList = arg("at", String(totalFrames))
  .split(",")
  .map((v) => Number(v.trim()))
  .filter((v) => Number.isFinite(v));

const WIDTH = 256;
const HEIGHT = 240;
let lastFrame = null;

const nes = new jsnes.NES({
  onFrame: (buffer) => {
    lastFrame = Int32Array.from(buffer);
  },
  onAudioSample: () => {},
  emulateSound: false,
});

nes.loadROM(readFileSync(romPath));

const wanted = new Set(atList);
const saved = [];
for (let frame = 1; frame <= totalFrames; frame++) {
  if (frame === startAt) {
    nes.buttonDown(1, jsnes.Controller.BUTTON_START); // Enter on the default mapping
  }
  if (frame === startAt + 6) nes.buttonUp(1, jsnes.Controller.BUTTON_START);

  nes.frame();

  if (wanted.has(frame) && lastFrame) {
    const stats = frameStats(lastFrame, WIDTH, HEIGHT);
    const file = outPath.replace(/\.png$/i, `-${frame}.png`);
    writePng(file, WIDTH, HEIGHT, stats.rgb);
    const top = [...stats.counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
    saved.push({ frame, file, nonBlack: stats.nonBlack, distinct: stats.distinct, top });
  }
}

console.log(`rom ${romPath}, ${totalFrames} frames, start at ${startAt}`);
for (const s of saved) {
  console.log(`\nframe ${s.frame} -> ${s.file}`);
  console.log(`  non-black ${s.nonBlack} px, ${s.distinct} distinct colours`);
  console.log("  top colours: " + s.top.map(([k, n]) => `${k}=${n}`).join(", "));
}
