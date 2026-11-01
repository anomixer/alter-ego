#!/usr/bin/env node
// Smoke test for the Apple IIgs port: boot the committed boot image in GSplus, wait for the title
// screen, press Return, and assert that Level 1 came up.  Both checks are pixel checks on GSplus'
// own F10 screenshots, so they prove the renderer actually drew those screens instead of merely
// that the emulator stayed alive.
//
// Usage (from the `iigs/` directory):  npm run test
//   --keep              leave GSplus running and keep the captures for inspection
//   --boot-timeout <s>  seconds allowed for the title (default 180; a 2.8 MHz build needs minutes)
//   --level-timeout <s> seconds allowed for Level 1 after Return (default 120)
// Environment: AE_GS_GSPLUS overrides the emulator path.
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { inflateSync } from 'node:zlib';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const IIGS_ROOT = resolve(SCRIPT_DIR, '..');
const REPO_ROOT = resolve(IIGS_ROOT, '..');

const IMAGE = join(REPO_ROOT, 'build', 'iigs', 'AlterEgo.2mg');
const KEGS = join(IIGS_ROOT, 'emu', 'gsplus-alterego.kegs');
const SHOTS = join(IIGS_ROOT, 'tmp', 'test');
const INPUT_HELPER = join(SCRIPT_DIR, 'gsplus-input.ps1');
const PNG_PATTERN = /^gsplus_screenshot_\d{8}_\d{6}\.png$/;

const args = process.argv.slice(2);
const keep = args.includes('--keep');
const optionValue = (name, fallback) => {
    const i = args.indexOf(name);
    return i >= 0 && args[i + 1] ? Number(args[i + 1]) : fallback;
};
const bootTimeoutMs = optionValue('--boot-timeout', 180) * 1000;
const levelTimeoutMs = optionValue('--level-timeout', 120) * 1000;
const gsplus = process.env.AE_GS_GSPLUS || 'C:\\dev\\emu\\GSplus\\gsplus.exe';

let gsplusPid = 0;

// Screens are classified by colours that only appear in quantity on the screen they belong to: the
// grey frame around the playfield, the title's orange logo, and the level's teal water.  The
// thresholds sit well away from the counts measured on the reference captures in
// iigs/docs/screenshots (title: grey 24 / orange 3132 / teal 28; Level 1: grey 9192 / teal 4688).
const SIGNATURES = [
    { name: 'grey', rgb: [187, 187, 187] },
    { name: 'orange', rgb: [255, 170, 68] },
    { name: 'teal', rgb: [0, 68, 68] },
    { name: 'white', rgb: [255, 255, 255] },
];

function classify(counts) {
    const isTitle = counts.grey < 500 && counts.teal < 500
        && counts.orange >= 1500 && counts.orange <= 7000 && counts.white >= 2000;
    const isLevel = counts.grey >= 4000 && counts.teal >= 1500;
    return { isTitle, isLevel };
}

function fail(message) {
    throw new Error(message);
}

function runHelper(action, timeoutSeconds = 20) {
    if (!gsplusPid) fail('GSplus is not running');
    const result = spawnSync('powershell', [
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', INPUT_HELPER,
        '-ProcessId', String(gsplusPid), '-Action', action, '-TimeoutSeconds', String(timeoutSeconds),
    ], { encoding: 'utf8' });
    if (result.error) fail(`could not run ${INPUT_HELPER}: ${result.error.message}`);
    if (result.status !== 0) fail(`GSplus input helper '${action}' failed: ${(result.stderr || '').trim()}`);
    return (result.stdout || '').trim();
}

// Minimal PNG reader (8-bit, non-interlaced RGB/RGBA) so the test needs no npm dependencies.
function decodePng(buffer) {
    const signature = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
    for (let i = 0; i < signature.length; i++) {
        if (buffer[i] !== signature[i]) fail('GSplus wrote something that is not a PNG');
    }

    let pos = 8;
    let width = 0;
    let height = 0;
    let bitDepth = 0;
    let colorType = 0;
    let interlace = 0;
    const chunks = [];
    while (pos + 8 <= buffer.length) {
        const length = buffer.readUInt32BE(pos);
        const type = buffer.toString('ascii', pos + 4, pos + 8);
        const data = buffer.subarray(pos + 8, pos + 8 + length);
        pos += 12 + length;
        if (type === 'IHDR') {
            width = data.readUInt32BE(0);
            height = data.readUInt32BE(4);
            bitDepth = data[8];
            colorType = data[9];
            interlace = data[12];
        } else if (type === 'IDAT') {
            chunks.push(data);
        } else if (type === 'IEND') {
            break;
        }
    }
    if (bitDepth !== 8 || interlace !== 0 || (colorType !== 2 && colorType !== 6)) {
        fail(`unsupported PNG layout (bit depth ${bitDepth}, colour type ${colorType}, interlace ${interlace})`);
    }

    const channels = colorType === 6 ? 4 : 3;
    const raw = inflateSync(Buffer.concat(chunks));
    const stride = width * channels;
    const pixels = Buffer.alloc(width * height * 4);
    let previous = Buffer.alloc(stride);

    for (let y = 0; y < height; y++) {
        const start = y * (stride + 1);
        const filter = raw[start];
        const line = Buffer.from(raw.subarray(start + 1, start + 1 + stride));
        for (let i = 0; i < stride; i++) {
            const a = i >= channels ? line[i - channels] : 0;
            const b = previous[i];
            const c = i >= channels ? previous[i - channels] : 0;
            switch (filter) {
                case 0:
                    break;
                case 1:
                    line[i] = (line[i] + a) & 0xff;
                    break;
                case 2:
                    line[i] = (line[i] + b) & 0xff;
                    break;
                case 3:
                    line[i] = (line[i] + ((a + b) >> 1)) & 0xff;
                    break;
                case 4: {
                    const p = a + b - c;
                    const pa = Math.abs(p - a);
                    const pb = Math.abs(p - b);
                    const pc = Math.abs(p - c);
                    const predictor = pa <= pb && pa <= pc ? a : (pb <= pc ? b : c);
                    line[i] = (line[i] + predictor) & 0xff;
                    break;
                }
                default:
                    fail(`unsupported PNG filter ${filter}`);
            }
        }
        for (let x = 0; x < width; x++) {
            const dst = (y * width + x) * 4;
            pixels[dst] = line[x * channels];
            pixels[dst + 1] = line[x * channels + 1];
            pixels[dst + 2] = line[x * channels + 2];
            pixels[dst + 3] = channels === 4 ? line[x * channels + 3] : 255;
        }
        previous = line;
    }

    return { width, height, pixels };
}

function countSignatures(image) {
    const counts = Object.fromEntries(SIGNATURES.map(s => [s.name, 0]));
    for (const { name, rgb } of SIGNATURES) {
        const [r, g, b] = rgb;
        for (let i = 0; i < image.pixels.length; i += 4) {
            if (image.pixels[i] === r && image.pixels[i + 1] === g && image.pixels[i + 2] === b) {
                counts[name] += 1;
            }
        }
    }
    return counts;
}

const listShots = () => readdirSync(SHOTS).filter(name => PNG_PATTERN.test(name));
const sleep = ms => new Promise(done => setTimeout(done, ms));

// Ask GSplus for its own screenshot (F10) and analyse it.  The file name carries a timestamp, so a
// leftover from the previous capture cannot be mistaken for a fresh one.
async function capture() {
    for (let attempt = 1; attempt <= 3; attempt++) {
        for (const name of listShots()) rmSync(join(SHOTS, name), { force: true });
        runHelper('f10');
        const deadline = Date.now() + 6000;
        while (Date.now() < deadline) {
            const shots = listShots();
            if (shots.length > 0) {
                const file = join(SHOTS, shots[0]);
                await sleep(150);  // GSplus streams the PNG to disk; let it finish
                const bytes = readFileSync(file);
                rmSync(file, { force: true });
                const image = decodePng(bytes);
                return { bytes, image, counts: countSignatures(image) };
            }
            await sleep(100);
        }
        if (gsplusExited()) fail('GSplus exited before the test finished');
        console.warn(`  F10 produced no screenshot (attempt ${attempt}/3)`);
    }
    return fail('GSplus never wrote a screenshot; is its window focused?');
}

let exitCode = null;
function gsplusExited() {
    return exitCode !== null;
}

async function main() {
    if (!existsSync(IMAGE)) fail(`boot image missing: ${IMAGE}`);
    if (!existsSync(KEGS)) fail(`GSplus configuration missing: ${KEGS}`);
    if (!existsSync(gsplus)) fail(`GSplus not found: ${gsplus} (set AE_GS_GSPLUS)`);
    if (!existsSync(INPUT_HELPER)) fail(`input helper missing: ${INPUT_HELPER}`);

    mkdirSync(SHOTS, { recursive: true });
    for (const name of readdirSync(SHOTS)) rmSync(join(SHOTS, name), { force: true });

    // GSplus writes screenshots into the directory named by `ssdir`; use a scratch copy of the
    // configuration so the checked-in one stays untouched.
    const scratchKegs = join(SHOTS, 'alterego-test.kegs');
    const kegsText = readFileSync(KEGS, 'utf8').replace(/^ssdir = .*$/m, `ssdir = ${SHOTS}`);
    writeFileSync(scratchKegs, kegsText);

    console.log('Alter Ego / Apple IIgs smoke test');
    console.log(`  image : ${IMAGE} (${statSync(IMAGE).size} bytes)`);
    console.log(`  emu   : ${gsplus}`);
    console.log(`  shots : ${SHOTS}`);

    const emulator = spawn(gsplus, ['-cfg', scratchKegs], { cwd: REPO_ROOT, stdio: 'ignore' });
    gsplusPid = emulator.pid;
    emulator.on('exit', code => { exitCode = code; });

    try {
        runHelper('window', 30);
        await sleep(1000);

        const bootStart = Date.now();
        let title = null;
        while (Date.now() - bootStart < bootTimeoutMs) {
            const shot = await capture();
            if (classify(shot.counts).isTitle) {
                title = shot;
                break;
            }
            await sleep(1500);
        }
        if (!title) fail(`the title screen did not appear within ${bootTimeoutMs / 1000}s`);
        writeFileSync(join(SHOTS, 'title.png'), title.bytes);
        console.log(`  title : after ${((Date.now() - bootStart) / 1000).toFixed(1)}s `
            + `(grey ${title.counts.grey}, orange ${title.counts.orange}, teal ${title.counts.teal})`);

        runHelper('return');
        const levelStart = Date.now();
        let level = null;
        while (Date.now() - levelStart < levelTimeoutMs) {
            await sleep(1500);
            const shot = await capture();
            if (classify(shot.counts).isLevel) {
                level = shot;
                break;
            }
        }
        if (!level) fail(`Level 1 did not appear within ${levelTimeoutMs / 1000}s after Return`);
        writeFileSync(join(SHOTS, 'level1.png'), level.bytes);
        console.log(`  level : after ${((Date.now() - levelStart) / 1000).toFixed(1)}s `
            + `(grey ${level.counts.grey}, teal ${level.counts.teal}, orange ${level.counts.orange})`);
        console.log('PASS');
    } finally {
        if (keep) {
            console.log(`  GSplus left running (pid ${gsplusPid}); captures in ${SHOTS}`);
        } else if (gsplusPid) {
            try {
                process.kill(gsplusPid);
            } catch {
                // already gone
            }
        }
    }
}

main().catch(error => {
    console.error(`FAIL: ${error.message}`);
    if (gsplusPid) {
        try {
            process.kill(gsplusPid);
        } catch {
            // already gone
        }
    }
    process.exitCode = 1;
});
