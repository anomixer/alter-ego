#!/usr/bin/env node
// Derive a ProDOS-order raw image (.po) from the tracked boot image.
//
// The deliverable in build/ is a 2IMG file: a 64-byte 2IMG header followed by the ProDOS
// blocks in ProDOS order (2IMG `format = 1`).  A .po is those blocks and nothing else, so
// the conversion strips the header — no data is converted and the block count does not
// change (20480 blocks = 10 MB).
//
// The 2IMG stays the source of truth (it is what the build writes and what `npm run test`
// boots); build/AlterEgo.po is generated and not committed.
//
// The same raw blocks are what Apple II/IIe hard-disk tooling calls an HDV — the file is
// identical, only the name differs — but the IIgs release is shipped as .2mg/.po.
//
// Usage: npm run make:po   (writes build/AlterEgo.po)

import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const IIGS_ROOT = join(ROOT, '..');
const TWO_IMG = join(IIGS_ROOT, 'build', 'AlterEgo.2mg');
const PO = join(IIGS_ROOT, 'build', 'AlterEgo.po');

function fail(message) {
    console.error(`make-po: ${message}`);
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
    fail(`2IMG image format ${format} is not ProDOS order — cannot strip it into a .po`);
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

writeFileSync(PO, raw);
const sha256 = createHash('sha256').update(raw).digest('hex').toUpperCase();
console.log(`image : ${TWO_IMG} (${image.length} bytes, 2IMG header ${headerSize})`);
console.log(`po    : ${PO} (${raw.length} bytes, ${rawBlocks} ProDOS blocks, SHA256 ${sha256})`);
