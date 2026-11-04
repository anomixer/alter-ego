#!/usr/bin/env node
'use strict';

/**
 * trim-2mg - shrink a ProDOS 8 volume inside a 2IMG file to the
 * smallest 0.5 MiB multiple that still contains every allocated block.
 *
 * The full System 6 image (`build/AlterEgo-full.2mg`) grew out of a stock 10 MB ProDOS
 * volume: System 6 plus `/ALTEREGO/AlterEgoGS.S16` fill only ~3.2 MB of it, so ~7 MB
 * of the file was empty volume.  This rewrites the same bytes into a smaller volume
 * instead of repacking the files through Cadius, so file data, directory entries,
 * resource forks and GS/OS extended entries are untouched.  The 800 KiB boot disk
 * (`build/AlterEgo.2mg`, from `npm run make:boot`) is already minimal, so the script
 * reports "nothing to do" there.
 *
 * What changes (three things, all size bookkeeping):
 *   1. the volume directory header's "total blocks" word (block 2, offset $29);
 *   2. the allocation bitmap's bits beyond the new end (marked in-use so nothing
 *      can ever allocate past the volume);
 *   3. the 2IMG header's block count and data size.
 * The bitmap blocks of the old, larger volume stay marked in use: freeing them
 * is possible but the three blocks are noise at this size, and leaving them
 * allocated keeps the bitmap exactly as ProDOS wrote it.
 *
 * The bitmap convention is ProDOS 8's: a 0 bit means in use, a 1 bit means free.
 * The volume directory file occupies block 2 onward and ends where the `next`
 * block chain says it does; the bitmap starts in the block after it and counts
 * `ceil(total / 4096)` blocks (one bit per block, 4096 blocks per bitmap block).
 *
 * Usage: node scripts/trim-2mg.mjs [--dry-run] [path/to/image.2mg]  (default: build/AlterEgo-full.2mg)
 */

import fs from 'node:fs';
import crypto from 'node:crypto';

const BLOCK = 512;
const DIR_HEADER_BLOCK = 2;
const TOTAL_BLOCKS_OFF = 0x29; // inside the volume directory header
const TWO_IMG_BLOCKS_OFF = 20;
const TWO_IMG_SIZE_OFF = 28;
const ROUND_BLOCKS = 1024; // 0.5 MiB

function die(msg) {
    console.error(`trim-2mg: ${msg}`);
    process.exit(1);
}

const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const imagePath = args.find((a) => !a.startsWith('--')) ?? 'build/AlterEgo-full.2mg';

const buf = fs.readFileSync(imagePath);
if (buf.subarray(0, 4).toString('latin1') !== '2IMG') die('not a 2IMG file');

const headerSize = buf.readUInt16LE(8);
const version = buf.readUInt16LE(10);
const format = buf.readUInt32LE(12);
const blocks = buf.readUInt32LE(20);
const dataOffset = buf.readUInt32LE(24);
const dataSize = buf.readUInt32LE(28);
if (version !== 1) die(`unsupported 2IMG version ${version}`);
if (format !== 1) die(`not ProDOS block order (format ${format})`);
if (dataOffset !== headerSize || headerSize + dataSize !== buf.length) {
    die('inconsistent 2IMG header (data offset / data size)');
}
if (dataSize !== blocks * BLOCK) die('2IMG block count disagrees with the data size');

const raw = buf.subarray(dataOffset);
const headerOff = DIR_HEADER_BLOCK * BLOCK;
const volumeTotal = raw.readUInt16LE(headerOff + TOTAL_BLOCKS_OFF);
if (volumeTotal !== blocks) {
    die(`volume header says ${volumeTotal} blocks, the image has ${blocks}`);
}
const volumeName = [...raw.subarray(headerOff + 5, headerOff + 20)]
    .map((c) => String.fromCharCode(c & 0x7f))
    .join('')
    .replace(/\0.*$/s, '');
if (!volumeName.startsWith('ALTEREGO')) die(`unexpected volume name "${volumeName}"`);

// The volume directory file starts at block 2; follow the next-block chain to
// the last directory block; the bitmap starts in the block after that.
let dirBlock = DIR_HEADER_BLOCK;
for (;;) {
    const next = raw.readUInt16LE(dirBlock * BLOCK + 2);
    if (next === 0) break;
    dirBlock = next;
    if (dirBlock < DIR_HEADER_BLOCK + 1 || dirBlock >= volumeTotal) die('bad volume directory chain');
}
const bitmapStart = dirBlock + 1;
const bitmapBlocks = Math.ceil(volumeTotal / 4096);

let used = 0;
let maxUsed = -1;
for (let i = 0; i < volumeTotal; i++) {
    const byteIdx = bitmapStart * BLOCK + (i >> 3);
    if (byteIdx >= raw.length) die(`the bitmap runs past the image at block ${i}`);
    if ((raw[byteIdx] & (1 << (i & 7))) === 0) {
        used++;
        if (i > maxUsed) maxUsed = i;
    }
}
if (maxUsed < 0) die('the volume has no allocated data blocks');

// Round up to a whole 0.5 MiB so the size stays a round number.
const newTotal = Math.ceil((maxUsed + 1) / ROUND_BLOCKS) * ROUND_BLOCKS;
const newSize = headerSize + newTotal * BLOCK;

const sha256 = (data) => crypto.createHash('sha256').update(data).digest('hex').toUpperCase();
console.log(`image     : ${imagePath} (${buf.length} bytes, ${blocks} blocks, SHA256 ${sha256(buf)})`);
console.log(`volume    : ${volumeName}, ${used} of ${volumeTotal} blocks in use, highest at ${maxUsed}`);
console.log(`bitmap    : blocks ${bitmapStart}-${bitmapStart + bitmapBlocks - 1} (${bitmapBlocks} blocks)`);
console.log(`trim      : ${blocks} blocks -> ${newTotal} blocks (${newSize} bytes, 0.5 MiB granularity)`);

if (newTotal >= volumeTotal) {
    console.log('trim      : nothing to do, the image already fits this size');
    process.exit(0);
}
if (dryRun) {
    console.log('trim      : dry run, no file written');
    process.exit(0);
}

const out = Buffer.alloc(newSize);
buf.copy(out, 0, 0, headerSize);
raw.copy(out, headerSize, 0, newTotal * BLOCK);

// 1. volume directory header: total blocks
out.writeUInt16LE(newTotal, headerSize + headerOff + TOTAL_BLOCKS_OFF);
// 2. bitmap: mark every block at/after the new end as in use (a 0 bit).  The smaller
//    volume may need fewer bitmap blocks, so use the new bitmap length, not the old one.
const newBitmapBlocks = Math.ceil(newTotal / 4096);
for (let i = newTotal; i < newBitmapBlocks * 4096; i++) {
    out[headerSize + bitmapStart * BLOCK + (i >> 3)] &= ~(1 << (i & 7));
}
// 3. 2IMG header: block count and data size
out.writeUInt32LE(newTotal, TWO_IMG_BLOCKS_OFF);
out.writeUInt32LE(newTotal * BLOCK, TWO_IMG_SIZE_OFF);

fs.writeFileSync(imagePath, out);
console.log(`trim      : wrote ${imagePath} (${out.length} bytes, SHA256 ${sha256(out)})`);
console.log('trim      : now run `npm run make:po` if the bare .po is needed');
