#!/usr/bin/env node
/*
 * FamiStudio/FamiTone project -> Apple II VERA PSG frame stream.
 *
 * Usage:
 *   node vera/tools/famitone2vera_psg.mjs input.ftm song-index output.psg
 *
 * FamiStudio renders isolated NES voices; this tool tracks their pitch and
 * envelope once per 60 Hz frame, then writes veramusic's [count,(reg,val)*]
 * PSG event format. This is a timbral approximation, not a register-level
 * FamiTone2 interpreter or NES APU emulator. DPCM is not included in .psg.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const RATE = 44100;
const TICK = 60;
const PSG_CLOCK = 25000000 / 512;
const NOISE_GAIN = Number(process.env.AE_NOISE_GAIN || 1.2);
const TRIANGLE_GAIN = 1.25;
const MUSIC_GAIN = Number(process.env.AE_MUSIC_GAIN || 2.0);
const PAN_BOTH = 0xC0;
const VERA_VOLUME = [
  0,4,8,12,16,17,18,20,21,22,23,25,26,28,30,31,
  33,35,37,40,42,45,47,50,53,56,60,63,67,71,75,80,
  85,90,95,101,107,113,120,127,135,143,151,160,170,180,191,202,
  214,227,241,255,270,286,303,321,341,361,382,405,429,455,482,511,
];
const VOICES = [
  { name: 'Square1', wave: 0x20, minHz: 65, maxHz: 1800 },
  { name: 'Square2', wave: 0x20, minHz: 65, maxHz: 1800 },
  { name: 'Triangle', wave: 0x80, minHz: 32, maxHz: 4000 },
  { name: 'Noise', wave: 0xC0, minHz: 80, maxHz: 6000 },
];

function boostVolume(volume) {
  if (!volume || MUSIC_GAIN <= 1) return volume;
  const target = Math.min(511, VERA_VOLUME[volume] * MUSIC_GAIN);
  let best = 0, bestDistance = Infinity;
  for (let i = 1; i < VERA_VOLUME.length; ++i) {
    const distance = Math.abs(VERA_VOLUME[i] - target);
    if (distance < bestDistance) { best = i; bestDistance = distance; }
  }
  return best;
}

function parseWav(file) {
  const b = fs.readFileSync(file);
  if (b.toString('ascii', 0, 4) !== 'RIFF' || b.toString('ascii', 8, 12) !== 'WAVE')
    throw new Error(`Not a RIFF/WAVE file: ${file}`);
  let p = 12, fmt, data;
  while (p + 8 <= b.length) {
    const id = b.toString('ascii', p, p + 4), n = b.readUInt32LE(p + 4), start = p + 8;
    if (id === 'fmt ') fmt = { format: b.readUInt16LE(start), channels: b.readUInt16LE(start + 2), rate: b.readUInt32LE(start + 4), bits: b.readUInt16LE(start + 14) };
    if (id === 'data') data = b.subarray(start, start + n);
    p = start + n + (n & 1);
  }
  if (!fmt || !data || fmt.format !== 1 || fmt.bits !== 16) throw new Error(`Expected 16-bit PCM WAV: ${file}`);
  const frames = Math.floor(data.length / (fmt.channels * 2));
  const mono = new Float32Array(frames);
  for (let i = 0; i < frames; ++i) {
    let s = 0;
    for (let c = 0; c < fmt.channels; ++c) s += data.readInt16LE((i * fmt.channels + c) * 2) / 32768;
    mono[i] = s / fmt.channels;
  }
  if (fmt.rate !== RATE) throw new Error(`FamiStudio stem must be 44100 Hz (got ${fmt.rate})`);
  return mono;
}

// Normalized autocorrelation over two frames, decimated 4:1. Unlike raw AMDF,
// this searches for a genuine periodic peak instead of preferring the smallest
// lag on the NES triangle's smooth ramps (which produced a false high tone).
function pitchAndRms(samples, frame, voice) {
  const hop = RATE / TICK;
  const start = frame * hop;
  let energy = 0;
  for (let i = 0; i < hop; ++i) { const x = samples[start + i] || 0; energy += x * x; }
  const rms = Math.sqrt(energy / hop);
  if (rms < 0.002) return { hz: 0, rms };

  const decim = 4, sr = RATE / decim, n = Math.floor((2 * hop) / decim);
  const lo = Math.max(2, Math.ceil(sr / voice.maxHz));
  const hi = Math.min(Math.floor(n / 2), Math.floor(sr / voice.minHz));
  const x = new Float32Array(n);
  let mean = 0;
  for (let i = 0; i < n; ++i) { x[i] = samples[start + i * decim] || 0; mean += x[i]; }
  mean /= n;
  let centeredEnergy = 0;
  for (let i = 0; i < n; ++i) { x[i] -= mean; centeredEnergy += x[i] * x[i]; }
  if (centeredEnergy < 1) return { hz: 0, rms };

  const corr = new Float32Array(hi + 2);
  for (let lag = lo; lag <= hi; ++lag) {
    let xy = 0, xx = 0, yy = 0;
    for (let i = 0; i < n - lag; ++i) {
      const a = x[i], b = x[i + lag];
      xy += a * b; xx += a * a; yy += b * b;
    }
    corr[lag] = xy / Math.sqrt((xx || 1) * (yy || 1));
  }
  // The earliest strong local maximum is the fundamental; later peaks are
  // octave/subharmonic multiples. Reject weak peaks during note transitions.
  for (let lag = lo + 1; lag < hi; ++lag) {
    if (corr[lag] >= 0.35 && corr[lag] > corr[lag - 1] && corr[lag] >= corr[lag + 1]) {
      const a = corr[lag - 1], b = corr[lag], c = corr[lag + 1];
      const offset = 0.5 * (a - c) / (a - 2 * b + c);
      return { hz: sr / (lag + (Number.isFinite(offset) ? offset : 0)), rms };
    }
  }
  return { hz: 0, rms };
}

function frameRms(samples, frame) {
  const hop = RATE / TICK, start = frame * hop;
  let energy = 0;
  for (let i = 0; i < hop; ++i) { const x = samples[start + i] || 0; energy += x * x; }
  return Math.sqrt(energy / hop);
}

function freqWord(hz) {
  return Math.max(0, Math.min(0xFFFF, Math.round(hz * 131072 / PSG_CLOCK)));
}

function usage() {
  console.log('Usage: node vera/tools/famitone2vera_psg.mjs <input.ftm> <song-index> <output.psg> [--mute-noise]');
  console.log('Set FAMISTUDIO and FTMPLAY to the FamiStudio and standalone ftmplay executables.');
}

function main(args) {
  if ((args.length !== 3 && args.length !== 4) || !/^\d+$/.test(args[1]) || (args.length === 4 && args[3] !== '--mute-noise')) { usage(); process.exitCode = 2; return; }
  const [input, indexText, output] = args;
  const muteNoise = args[3] === '--mute-noise';
  const songIndex = Number(indexText);
  const exe = process.env.FAMISTUDIO || 'FamiStudio.exe';
  if (!fs.existsSync(input)) throw new Error(`Input not found: ${input}`);
  if (!fs.existsSync(exe)) throw new Error(`FamiStudio.exe not found: ${exe} (set FAMISTUDIO)`);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ae-fami-psg-'));
  try {
    const stemBase = path.join(tmp, 'stem.wav');
    const r = spawnSync(exe, [input, 'wav-export', stemBase, `-export-songs:${songIndex}`, '-wav-export-separate-channels', '-wav-export-rate:44100'], { encoding: 'utf8', windowsHide: true });
    if (r.error) throw r.error;
    if (r.status !== 0) throw new Error(`FamiStudio export failed (${r.status}): ${r.stderr || r.stdout}`);
    const stems = VOICES.map(v => {
      const p = stemBase.replace(/\.wav$/i, `_${v.name}.wav`);
      if (!fs.existsSync(p)) throw new Error(`FamiStudio did not create ${path.basename(p)}`);
      return parseWav(p);
    });
    const dpcmPath = stemBase.replace(/\.wav$/i, '_DPCM.wav');
    const dpcm = fs.existsSync(dpcmPath) ? parseWav(dpcmPath) : null;
    const totalSamples = Math.max(...stems.map(s => s.length));
    const frames = Math.ceil(totalSamples / (RATE / TICK));
    let peakRms = 0;
    for (let v = 0; v < VOICES.length; ++v) {
      for (let f = 0; f < frames; ++f) {
        const rms = frameRms(stems[v], f);
        if (rms > peakRms) peakRms = rms;
      }
    }
    const events = [];
    const regState = new Uint8Array(64);
    let activeFrames = 0;
    for (let f = 0; f < frames; ++f) {
      const writes = new Map();
      const emit = (reg, value) => {
        if (regState[reg] !== value) {
          writes.set(reg, value);
          regState[reg] = value;
        }
      };
      for (let v = 0; v < VOICES.length; ++v) {
        const { hz: detectedHz, rms } = pitchAndRms(stems[v], f, VOICES[v]);
        const base = v * 4;
        if (v === 3 && muteNoise) {
          emit(base + 2, 0);
          continue;
        }
        // Noise has no stable fundamental, so pitch correlation is invalid.
        // Keep the stem's approved amplitude envelope here; a second pass
        // applies the exact per-note APU period from the source FTM.
        if (v === 3 && rms >= 0.002) {
          ++activeFrames;
          const freq = freqWord(14000);
          const rawVol = Math.max(1, Math.min(63, Math.round(Math.pow(rms / (peakRms || 1), 0.65) * 61 * NOISE_GAIN)));
          const vol = boostVolume(rawVol);
          emit(base, freq & 0xFF);
          emit(base + 1, (freq >> 8) & 0xFF);
          emit(base + 2, PAN_BOTH | vol);
          emit(base + 3, VOICES[v].wave);
          continue;
        }
        if (rms < 0.002 || detectedHz <= 0) {
          emit(base + 2, 0);
          continue;
        }
        ++activeFrames;
        const hz = detectedHz;
        const freq = freqWord(hz);
        // RMS-to-volume is intentionally per-frame: it reproduces the NES
        // channel's note envelope rather than imposing a fixed VERA level.
        const gain = v === 2 ? TRIANGLE_GAIN : 1;
        const rawVol = Math.max(1, Math.min(63, Math.round(Math.pow(rms / (peakRms || 1), 0.65) * 61 * gain)));
        const vol = boostVolume(rawVol);
        emit(base, freq & 0xFF);
        emit(base + 1, (freq >> 8) & 0xFF);
        emit(base + 2, PAN_BOTH | vol);
        emit(base + 3, VOICES[v].wave);
      }
      const pairs = [...writes.entries()];
      events.push(pairs.length, ...pairs.flat());
    }
    // Reset the four used voice volumes before looping so register elision
    // cannot leave a note held across the loop boundary.
    events.push(4, 2, 0, 6, 0, 10, 0, 14, 0);
    // Loop at frame zero, matching FamiStudio's whole-song repeat.
    events.push(0xFF, 0, 0);
    fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true });
    fs.writeFileSync(output, Buffer.from(events));
    if (!muteNoise) {
      const patcher = path.join(path.dirname(fileURLToPath(import.meta.url)), 'patch_psg_noise_from_ftm.mjs');
      const ftmplay = process.env.FTMPLAY || 'C:/dev/veramusic/tools/ftmplay.exe';
      const patched = spawnSync(process.execPath, [patcher, input, String(songIndex), output], {
        encoding: 'utf8', windowsHide: true, env: { ...process.env, FTMPLAY: ftmplay },
      });
      if (patched.error) throw patched.error;
      if (patched.status !== 0) throw new Error(`FTM noise mapping failed: ${patched.stderr || patched.stdout}`);
      if (patched.stdout) process.stdout.write(patched.stdout);
    }
    const dpcmRms = dpcm ? Math.sqrt(dpcm.reduce((a, x) => a + x * x, 0) / dpcm.length) : 0;
    console.log(`Wrote ${output}: ${frames} frames (${(frames / TICK).toFixed(2)} s), ${events.length} bytes`);
    console.log(`Tracked 4 PSG stems; active voice-frames=${activeFrames}. DPCM stem RMS=${dpcmRms.toFixed(4)} (DPCM is not encoded in .psg).`);
    if (dpcmRms > 0.001) console.warn('WARNING: this song uses DPCM; its sample channel is omitted from this PSG-only output.');
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  try { main(process.argv.slice(2)); } catch (e) { console.error(`[FAILED] ${e.message}`); process.exitCode = 1; }
}
