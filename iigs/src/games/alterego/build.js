#!/usr/bin/env node
'use strict';

/**
 * build.js -- Alter Ego title-screen PoC build script
 *
 * 1. Generate the palette management (palettes.s, pal_transitions.s, pal_defs.s)
 *    from palettes/.
 * 2. Convert the CHR-ROM held by PPU.s into the 64KB tiledata bank and assemble
 *    the game.  The NES code is the original HEAD C build at $8000-$FFFF,
 *    placed by rom.s; the support/shim code is below $8000 in the same bank.
 */

const fs = require('fs');
const path = require('path');
const { generatePalettes, PaletteError } = require('../../../scripts/generate-palette-transitions.js');
const { buildNromGame } = require('../../../scripts/lib/nromBuild.js');

const palettesDir = path.join(__dirname, 'palettes');
try {
  generatePalettes({
    transitionsFile: path.join(palettesDir, 'transitions.txt'),
    palettesDir,
    outDir: __dirname,
  });
} catch (e) {
  if (!(e instanceof PaletteError)) throw e;
  console.error(`Error: ${e.message}`);
  process.exit(1);
}

buildNromGame(__dirname, 'AlterEgo.s');

// Publish the assembled load file next to the boot image, i.e. in build/iigs/ (the VERA port
// keeps its images in build/a2vera/ the same way).  Merlin32 writes its DSK into the game
// directory, which stays local and is ignored.
const publishDir = path.join(__dirname, '..', '..', '..', '..', 'build', 'iigs');
fs.mkdirSync(publishDir, { recursive: true });
fs.copyFileSync(path.join(__dirname, 'AlterEgoGS'), path.join(publishDir, 'AlterEgoGS'));
console.log(`  published ${path.relative(process.cwd(), path.join(publishDir, 'AlterEgoGS'))}`);

