#!/usr/bin/env node
/* Apply FamiTracker's per-frame NES noise pitch to an existing VERA PSG stream.
 * Existing channel volumes and all other voices are kept intact. */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const PSG_CLOCK = 25000000 / 512;
const FTMPLAY = process.env.FTMPLAY || 'C:/dev/veramusic/tools/ftmplay.exe';

function run(input, songIndex, psgPath) {
  if (!fs.existsSync(input)) throw new Error(`FTM not found: ${input}`);
  if (!fs.existsSync(psgPath)) throw new Error(`PSG not found: ${psgPath}`);
  if (!fs.existsSync(FTMPLAY)) throw new Error(`ftmplay not found: ${FTMPLAY} (set FTMPLAY)`);
  const tmp = path.join(os.tmpdir(), `ae-noise-${process.pid}.txt`);
  try {
    const r = spawnSync(FTMPLAY, [input, String(songIndex), '--noise-freqs', tmp],
      { encoding: 'utf8', windowsHide: true });
    if (r.error) throw r.error;
    if (r.status !== 0) throw new Error(`ftmplay failed (${r.status}): ${r.stderr || r.stdout}`);
    const source = fs.readFileSync(tmp, 'utf8').trim().split(/\r?\n/).map(Number);
    if (!source.length || source.some(x => !Number.isFinite(x) || x < 0))
      throw new Error('Invalid noise-frequency timeline from ftmplay');

    const bytes = fs.readFileSync(psgPath);
    const records = [];
    let p = 0;
    while (p < bytes.length && bytes[p] !== 0xFF) {
      const count = bytes[p++];
      if (count > 64 || p + count * 2 > bytes.length) throw new Error(`Invalid PSG record at frame ${records.length}`);
      const pairs = [];
      for (let i = 0; i < count; ++i) pairs.push([bytes[p++], bytes[p++]]);
      records.push(pairs);
    }
    if (p + 2 >= bytes.length || bytes[p] !== 0xFF) throw new Error('PSG loop marker is missing');
    const tail = bytes.subarray(p);
    if (!records.length) throw new Error('PSG has no frames');

    // Fill silent FTM frames with the latest note's pitch so an active WAV
    // envelope can begin/end a few frames away from the parsed note boundary.
    let first = source.find(x => x > 0) || 14000;
    let held = first;
    const timeline = source.map(hz => {
      if (hz > 0) held = hz;
      return held;
    });
    let activeFrames = 0, minHz = Infinity, maxHz = 0;
    const rewritten = [];
    const state = new Uint8Array(64);
    for (let f = 0; f < records.length; ++f) {
      const pairs = records[f];
      for (const [reg, value] of pairs) state[reg] = value;
      if (state[14] & 0x3F) {
        const sourceFrame = Math.min(timeline.length - 1,
          Math.floor(f * timeline.length / records.length));
        const hz = timeline[sourceFrame] || 14000;
        const word = Math.max(0, Math.min(0xFFFF, Math.round(hz * 131072 / PSG_CLOCK)));
        for (const [reg, value] of [[12, word & 0xFF], [13, word >> 8]]) {
          if (state[reg] !== value) {
            pairs.push([reg, value]);
            state[reg] = value;
          }
        }
        activeFrames++;
        minHz = Math.min(minHz, hz);
        maxHz = Math.max(maxHz, hz);
      }
      if (pairs.length > 64) throw new Error(`Frame ${f} now has more than 64 register writes`);
      rewritten.push(pairs.length, ...pairs.flat());
    }
    const out = Buffer.from([...rewritten, ...tail]);
    fs.writeFileSync(psgPath, out);
    console.log(`${path.basename(psgPath)}: dynamic NES noise pitch on ${activeFrames} frames, ${Math.round(minHz)}-${Math.round(maxHz)} Hz; aligned ${timeline.length} FTM frames to ${records.length} PSG frames.`);
  } finally {
    if (fs.existsSync(tmp)) fs.rmSync(tmp, { force: true });
  }
}

const [, , input, songArg, psg] = process.argv;
if (!input || !/^\d+$/.test(songArg || '') || !psg) {
  console.error('Usage: node vera/tools/patch_psg_noise_from_ftm.mjs <input.ftm> <song-index> <music.psg>');
  process.exit(2);
} else {
  try { run(input, Number(songArg), psg); }
  catch (e) { console.error(`[FAILED] ${e.message}`); process.exitCode = 1; }
}
