// Assemble the NES ROM (iNES format) for the Alter Ego web player.
//
// The default build *compiles the ROM from the sources in this repository* —
// the same `src/` tree that `make all` uses (cc65 + ca65 + ld65) — so the web
// page always plays a ROM produced here instead of shipping a binary.
//
// Two sources:
//   (default)          compile `src/` with cc65/ca65/ld65 (see the root Makefile)
//   --from <file.nes>  stage an existing ROM (e.g. the original v1.02 release)
//
// The ROM is written to build/, which is gitignored, together with a base64 copy
// so the standalone page also runs from file:// (where fetch() is blocked).
//
// Notes on the toolchain:
//   * `src/nes.lib` in the repository is the historical cc65 library and ld65
//     V2.19 rejects it ("Wrong data version"), so the installed cc65 `nes.lib`
//     is linked instead.  The game links the same modules either way.
//   * `web/nes/nes-cc65-2.19.cfg` is `src/nes.cfg` with two changes that V2.19
//     needs: the modern `__STACKSIZE__: type = weak, value = …` symbol syntax
//     and an `ONCE` segment (the installed library has one).  Keep it in sync
//     with `src/nes.cfg`.
//
// Usage: node build-rom.mjs [--from <file.nes>] [--out <file>]
// Environment: CC65_BIN overrides the cc65 bin directory.

import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, "..", "..");

function arg(name, fallback) {
  const i = process.argv.indexOf("--" + name);
  return i >= 0 ? process.argv[i + 1] : fallback;
}

const from = arg("from", null);
const outFile = resolve(arg("out", join(here, "build", "alterego.nes")));
const work = join(here, "build", "target");

function cc65Bin() {
  const candidates = [
    process.env.CC65_BIN,
    "C:\\dev\\cc65\\bin",
    "C:\\cc65\\bin",
  ].filter(Boolean);
  for (const dir of candidates) {
    if (existsSync(join(dir, "cc65.exe")) || existsSync(join(dir, "cc65"))) return dir;
  }
  return null; // fall back to PATH
}

function tool(dir, name) {
  if (!dir) return name;
  const exe = [join(dir, `${name}.exe`), join(dir, name)].find((p) => existsSync(p));
  return exe ?? name;
}

function run(bin, name, args) {
  const cmd = tool(bin, name);
  const res = spawnSync(cmd, args, { cwd: repo, encoding: "utf8" });
  if (res.stdout) process.stdout.write(res.stdout);
  if (res.stderr) process.stderr.write(res.stderr);
  if (res.error) throw new Error(`${cmd}: ${res.error.message}`);
  if (res.status !== 0) throw new Error(`${cmd} exited with ${res.status}`);
}

function compileFromSource() {
  const bin = cc65Bin();
  if (!bin) {
    console.warn("warning: cc65 not found (set CC65_BIN); falling back to PATH");
  }
  console.log(`cc65: ${bin ?? "PATH"}`);
  mkdirSync(work, { recursive: true });

  // The root Makefile's five steps, with the outputs redirected into build/target.
  run(bin, "cc65", ["--include-dir", "./src", "-Oi", "src/game.c", "--add-source", "-o", join(work, "game.s")]);
  run(bin, "ca65", ["src/crt0.s", "--include-dir", "./src", "-o", join(work, "crt0.o")]);
  run(bin, "ca65", ["src/neslib.s", "--include-dir", "./src", "-o", join(work, "neslib.o")]);
  run(bin, "ca65", [join(work, "game.s"), "-o", join(work, "game.o")]);

  // src/nes.lib is the historical library (wrong data version for V2.19), so
  // use the one installed next to cc65 when it exists.
  const installedLib = bin ? join(bin, "..", "lib", "nes.lib") : null;
  const lib = installedLib && existsSync(installedLib) ? installedLib : join(repo, "src", "nes.lib");
  console.log(`library: ${lib}`);

  run(bin, "ld65", [
    "-C", join(here, "nes-cc65-2.19.cfg"),
    "-o", join(work, "alterego.nes"),
    join(work, "crt0.o"),
    join(work, "game.o"),
    join(work, "neslib.o"),
    lib,
  ]);

  const rom = readFileSync(join(work, "alterego.nes"));
  if (rom.subarray(0, 4).toString("latin1") !== "NES\x1a") {
    throw new Error("ld65 output is not an iNES ROM");
  }
  return rom;
}

function stageExisting(path) {
  const rom = readFileSync(path);
  const tag = rom.subarray(0, 4).toString("latin1");
  if (tag !== "NES\x1a") throw new Error(`${path} is not an iNES ROM`);
  return rom;
}

const rom = from ? stageExisting(resolve(from)) : compileFromSource();

mkdirSync(dirname(outFile), { recursive: true });
writeFileSync(outFile, rom);

const sha = createHash("sha256").update(rom).digest("hex").toUpperCase();
console.log(`${outFile}: ${rom.length} bytes  PRG ${rom[4] * 16384}  CHR ${rom[5] * 8192}  mapper ${(rom[7] & 0xf0) | (rom[6] >> 4)}`);
console.log(`sha256 ${sha}`);

const b64File = join(dirname(outFile), "rom-base64.js");
writeFileSync(b64File, `window.AE_ROM_B64 = "${rom.toString("base64")}";\n`);
console.log(`${b64File}: ${rom.toString("base64").length} base64 chars`);
