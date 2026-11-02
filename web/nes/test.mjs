// Smoke test for the web player: boot the ROM headlessly in jsnes, wait for the
// title, press Start, wait for Level 1 — asserting *pixels*, not just that the
// emulator is alive. Exit code 0 = PASS, 1 = FAIL.
//
//   node test.mjs [--rom build/alterego.nes] [--keep]
//
// Captures are written to build/shots/title.png and build/shots/level1.png.
// The signatures are colours that only appear in quantity on their screen
// (measured on the original v1.02 ROM through jsnes): the title is mostly black
// with the blue/gold logo, Level 1 adds the white frame and the blue playfield.

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

const WIDTH = 256;
const HEIGHT = 240;
const BLUE = "0,25,188";
const GOLD = "255,171,60";

const TITLE_MIN = { nonBlack: 2500, maxNonBlack: 12000, blue: 700, gold: 500 };
const LEVEL_MIN = { nonBlack: 10000, blue: 1200 };

let lastFrame = null;
const nes = new jsnes.NES({
  onFrame: (buffer) => {
    lastFrame = Int32Array.from(buffer);
  },
  onAudioSample: () => {},
  emulateSound: false,
});
nes.loadROM(readFileSync(romPath));

function snapshot(tag) {
  const stats = frameStats(lastFrame, WIDTH, HEIGHT);
  const file = join(here, "build", "shots", `${tag}.png`);
  writePng(file, WIDTH, HEIGHT, stats.rgb);
  return { stats, file };
}

function count(stats, colour) {
  return stats.counts.get(colour) || 0;
}

// Runs frames until `check` accepts a snapshot; returns {frame, stats, file}.
function runUntil(label, maxFrames, check, minFrame = 0) {
  for (let frame = 0; frame < maxFrames; frame++) {
    nes.frame();
    if (frame < minFrame) continue; // skip the cold-boot credits intro
    if ((frame & 3) !== 0) continue; // sample every 4th frame
    const stats = frameStats(lastFrame, WIDTH, HEIGHT);
    if (check(stats)) {
      const file = join(here, "build", "shots", `${label}.png`);
      writePng(file, WIDTH, HEIGHT, stats.rgb);
      return { frame, stats, file };
    }
  }
  const stats = frameStats(lastFrame, WIDTH, HEIGHT);
  const file = join(here, "build", "shots", `${label}.png`);
  writePng(file, WIDTH, HEIGHT, stats.rgb);
  return { frame: maxFrames, stats, file };
}

function describe(stats) {
  return `non-black ${stats.nonBlack}, blue ${count(stats, BLUE)}, gold ${count(stats, GOLD)}, ${stats.distinct} colours`;
}

let pass = true;

console.log(`rom ${romPath}`);
const title = runUntil("title", 1800, (s) =>
  s.nonBlack >= TITLE_MIN.nonBlack &&
  s.nonBlack <= TITLE_MIN.maxNonBlack &&
  count(s, BLUE) >= TITLE_MIN.blue &&
  count(s, GOLD) >= TITLE_MIN.gold,
  240, // a cold boot shows the credits screen for roughly its first 240 frames
);
console.log(`title  after ${title.frame} frames: ${describe(title.stats)}  -> ${title.file}`);
if (title.stats.nonBlack < TITLE_MIN.nonBlack || title.stats.nonBlack > TITLE_MIN.maxNonBlack) {
  console.log(`  FAIL: title non-black ${title.stats.nonBlack} outside ${TITLE_MIN.nonBlack}..${TITLE_MIN.maxNonBlack}`);
  pass = false;
} else if (count(title.stats, BLUE) < TITLE_MIN.blue) {
  console.log(`  FAIL: title blue ${count(title.stats, BLUE)} < ${TITLE_MIN.blue}`);
  pass = false;
} else if (count(title.stats, GOLD) < TITLE_MIN.gold) {
  console.log(`  FAIL: title gold ${count(title.stats, GOLD)} < ${TITLE_MIN.gold} (credits screen?)`);
  pass = false;
}

// Enter = NES Start on jsnes' default mapping.  The title accepts the press only
// after its intro (an early press is ignored), so press once, then keep pressing
// every few seconds until Level 1 shows up.
function pressStart() {
  nes.buttonDown(1, jsnes.Controller.BUTTON_START);
  for (let i = 0; i < 6; i++) nes.frame();
  nes.buttonUp(1, jsnes.Controller.BUTTON_START);
}

let level = null;
for (let attempt = 0; attempt < 8 && !level; attempt++) {
  pressStart();
  level = runUntil(
    "level1",
    240,
    (s) => s.nonBlack >= LEVEL_MIN.nonBlack && count(s, BLUE) >= LEVEL_MIN.blue,
  );
  if (level.frame >= 240) level = null;
}
level = level ?? {
  frame: -1,
  stats: frameStats(lastFrame, WIDTH, HEIGHT),
  file: join(here, "build", "shots", "level1.png"),
};
console.log(`level  after ${level.frame} frames: ${describe(level.stats)}  -> ${level.file}`);
if (level.stats.nonBlack < LEVEL_MIN.nonBlack) {
  console.log(`  FAIL: level non-black ${level.stats.nonBlack} < ${LEVEL_MIN.nonBlack}`);
  pass = false;
} else if (count(level.stats, BLUE) < LEVEL_MIN.blue) {
  console.log(`  FAIL: level blue ${count(level.stats, BLUE)} < ${LEVEL_MIN.blue}`);
  pass = false;
}

console.log(pass ? "PASS" : "FAIL");
process.exit(pass ? 0 : 1);
