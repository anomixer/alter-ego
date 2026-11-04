#!/usr/bin/env node
// Build the 800 KiB boot disk: the smallest ProDOS volume that holds GS/OS, the game and nothing
// else.  ProDOS 8 boots the disk, START.GS.OS starts GS/OS, and GS/OS launches /SYSTEM/START as its
// startup program - which is the game, so there is no Finder and no desktop.
//
// The GS/OS side is `dist/GSBoot.2mg`: the minimal boot set from the silky-gs distribution
// (`dist/GSBoot.2mg`, made by that repository's `scripts/make-boot-disk.js` from its `dist/GSOS.2mg`
// System 6 disk).  It is 1,600 blocks with 478 used, so the 613-block game still leaves ~250 KiB
// free, and every file on the disk is either GS/OS or the game.
//
// The game on this disk is the **one-way-exit build** (`build.js --exitscreen`): there is no Finder here, so Q
// cannot quit to anything, so it saves the preferences, leaves the machine on a screen that says the game
// has exited, and stops (see the comment at `quit` in `src/games/alterego/Main.s`).  This script builds
// it, so the image can never be packed with a copy that quits to the Finder.
//
// Usage (from the `iigs/` directory):  npm run make:boot
// Environment: CADIUS overrides the Cadius path (default: `config.cadius` in package.json).
import { spawnSync } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const IIGS_ROOT = resolve(SCRIPT_DIR, '..');
const TEMPLATE = join(IIGS_ROOT, 'dist', 'GSBoot.2mg');
const README = join(IIGS_ROOT, 'dist', 'README.TXT');
const APP_BUILD = join(IIGS_ROOT, 'src', 'games', 'alterego', 'build.js');
const APP = join(IIGS_ROOT, 'build', 'AlterEgoGS.exit');
const IMAGE = join(IIGS_ROOT, 'build', 'AlterEgo.2mg');
const STAGE = join(IIGS_ROOT, 'tmp', 'make-boot');
const VOLUME = 'ALTEREGO';
const BLOCK = 512;

const pkg = JSON.parse(readFileSync(join(IIGS_ROOT, 'package.json'), 'utf8'));
const cadius = process.env.CADIUS || pkg.config.cadius;

function fail(message) {
    console.error(`make-boot: ${message}`);
    process.exit(1);
}

// Cadius reports its failures on stderr but still exits 0 for ADDFILE, so the text is checked as
// well.  The volume holds GS/OS' `Error.Msg`, so CATALOG is matched on the failure wording instead.
function cadiusRun(argv) {
    const result = spawnSync(cadius, argv, { encoding: 'utf8' });
    if (result.error) fail(`could not run ${cadius}: ${result.error.message}`);
    const text = `${result.stdout || ''}${result.stderr || ''}`;
    const failed = argv[0] === 'CATALOG'
        ? /(can't|unable|not found|does not exist|error (?:adding|cataloging))/i.test(text)
        : /error/i.test(text);
    if (result.status !== 0 || failed) fail(`cadius ${argv[0]} failed:\n${text.trim()}`);
    return text;
}

// A 2IMG checksum is a convenience, so the template and the output are described the same way.
const sha256 = (file) => createHash('sha256').update(readFileSync(file)).digest('hex').toUpperCase();

// Assemble the boot-disk copy first: one binary, two builds, and only this one restarts on Q.
const build = spawnSync(process.execPath, [APP_BUILD, '--exitscreen'], { cwd: join(IIGS_ROOT, 'src', 'games', 'alterego'), encoding: 'utf8' });
if (build.error) fail(`could not run build.js: ${build.error.message}`);
if (build.status !== 0) fail(`the boot-disk build failed:\n${`${build.stdout || ''}${build.stderr || ''}`.trim()}`);

for (const [label, file] of [['template', TEMPLATE], ['application', APP], ['README', README]]) {
    if (!existsSync(file)) fail(`missing ${label} ${file}`);
}

const template = readFileSync(TEMPLATE);
if (template.subarray(0, 4).toString('latin1') !== '2IMG') fail('dist/GSBoot.2mg is not a 2IMG file');
const headerSize = template.readUInt16LE(8);
const blocks = template.readUInt32LE(20);
const dataSize = template.readUInt32LE(28);
if (template.readUInt32LE(12) !== 1) fail('dist/GSBoot.2mg is not in ProDOS block order');
if (headerSize !== 64 || dataSize !== blocks * BLOCK || headerSize + dataSize !== template.length) {
    fail('dist/GSBoot.2mg has an inconsistent 2IMG header');
}
if (blocks !== 1600) fail(`dist/GSBoot.2mg has ${blocks} blocks, expected the 800 KiB template (1600)`);
const volumeName = [...template.subarray(headerSize + 2 * BLOCK + 5, headerSize + 2 * BLOCK + 20)]
    .map((c) => String.fromCharCode(c & 0x7f))
    .join('')
    .replace(/\0.*$/s, '');
if (!volumeName.startsWith('GSBOOT')) fail(`dist/GSBoot.2mg holds "${volumeName}", expected the GSBoot template`);

// Stage the two files Cadius adds under the names the disk expects.  A `#B3DB03` / `#B00000` suffix
// is how ADDFILE is told the ProDOS type and aux type; the name on the disk is the part before `#`.
rmSync(STAGE, { recursive: true, force: true });
mkdirSync(STAGE, { recursive: true });
copyFileSync(APP, join(STAGE, 'Start#B3DB03'));
copyFileSync(README, join(STAGE, 'README.TXT#B00000'));

copyFileSync(TEMPLATE, IMAGE);
cadiusRun(['RENAMEVOLUME', IMAGE, VOLUME]);
cadiusRun(['ADDFILE', IMAGE, `/${VOLUME}/System`, join(STAGE, 'Start#B3DB03')]);
cadiusRun(['ADDFILE', IMAGE, `/${VOLUME}`, join(STAGE, 'README.TXT#B00000')]);

// Cadius exits 0 even when ADDFILE cannot copy a file, so check the catalogue itself.
const catalog = cadiusRun(['CATALOG', IMAGE]);
const problems = [];
if (!/^\s+Start\s+S16 /m.test(catalog)) problems.push('Start (S16) is not in /SYSTEM');
if (!/^\s+README\.TXT\s+(?:TXT|SRC)\s+\$0000/m.test(catalog)) problems.push('README.TXT (type $B0) is not at the root');
const totals = catalog.match(/Block\s*:\s*(\d+)\s+Free\s*:\s*(\d+)\s+File\s*:\s*(\d+)/);
if (!totals) problems.push('the catalogue has no volume totals line');
else if (Number(totals[1]) !== 1600) problems.push(`the volume reports ${totals[1]} blocks, expected 1600`);
if (problems.length) fail(problems.join('; '));

const freeBlocks = Number(totals[2]);
if (freeBlocks < 0) fail('the volume is overfull');
const volumeBytes = statSync(IMAGE).size;
writeFileSync(join(STAGE, 'CATALOG.txt'), catalog);
rmSync(STAGE, { recursive: true, force: true });

console.log(`boot disk : ${IMAGE}`);
console.log(`volume    : ${VOLUME}, 1,600 blocks (800 KiB), ${freeBlocks} free, ${totals[3]} files`);
console.log(`template  : dist/GSBoot.2mg (${template.length} bytes, SHA256 ${sha256(TEMPLATE)})`);
console.log(`game      : build/AlterEgoGS.exit as /SYSTEM/START (S16, ${statSync(APP).size} bytes, SHA256 ${sha256(APP)})`);
console.log(`image     : ${volumeBytes} bytes, SHA256 ${sha256(IMAGE)}`);
