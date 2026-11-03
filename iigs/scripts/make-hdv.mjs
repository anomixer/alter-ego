#!/usr/bin/env node
// Derive a raw ProDOS hard-disk image (HDV) from the tracked boot image.
//
// The deliverable in build/ is a 2IMG file: a 64-byte 2IMG header followed by the ProDOS
// blocks in ProDOS order (2IMG `format = 1`).  Emulators that mount a hard disk want the
// blocks alone, so the HDV is the 2IMG file minus its header — no data is converted.
//
// The 2IMG stays the source of truth (it is what the build writes and what `npm run test`
// boots); build/AlterEgo.hdv is generated and not committed.
//
// Usage: npm run make:hdv   (writes build/AlterEgo.hdv)

import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const IIGS_ROOT = join(ROOT, '..');
const TWO_IMG = join(IIGS_ROOT, 'build', 'AlterEgo.2mg');
const HDV = join(IIGS_ROOT, 'build', 'AlterEgo.hdv');

function fail(message) {
    console.error(`make-hdv: ${message}`);
    process.exit(1);
}

const image = readFileSync(TWO_IMG);
if (image.length < 64 || image.toString('latin1', 0, 4) !== '2IMG') {
    fail(`${TWO_IMG} is not a 2IMG file (no "2IMG" signature) — rebuild or repackage it first`);
}

const headerSize = image.readUInt16LE(8);
const format = image[12];
const blocks = image.readUInt16LE(14);
if (headerSize < 64 || headerSize > image.length) {
    fail(`2IMG header size ${headerSize} does not fit the file`);
}
if (format !== 1) {
    // 0 = DOS 3.3 order, 2 = NIB.  A DOS-order 2IMG interleaves each 512-byte block's
    // halves, so stripping the header would not produce a ProDOS disk.
    fail(`2IMG image format ${format} is not ProDOS order — cannot strip it into an HDV`);
}

const raw = image.subarray(headerSize);
if (raw.length % 512 !== 0) {
    fail(`block data is ${raw.length} bytes, not a whole number of 512-byte blocks`);
}
const rawBlocks = raw.length / 512;
if (blocks !== 0 && blocks !== rawBlocks) {
    fail(`2IMG says ${blocks} blocks but the file holds ${rawBlocks}`);
}
if (raw.indexOf(Buffer.from('ALTEREGO')) < 0) {
    fail('the ProDOS volume name ALTEREGO is not in the block data — is this the Alter Ego image?');
}

writeFileSync(HDV, raw);
const sha256 = createHash('sha256').update(raw).digest('hex').toUpperCase();
console.log(`image : ${TWO_IMG} (${image.length} bytes, 2IMG header ${headerSize})`);
console.log(`hdv   : ${HDV} (${raw.length} bytes, ${rawBlocks} ProDOS blocks, SHA256 ${sha256})`);
