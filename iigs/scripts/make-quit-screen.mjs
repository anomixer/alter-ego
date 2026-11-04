// Builds the screen the game leaves behind when Q -> Y quits on the 800 KiB boot disk.
//
// The boot disk has no Finder and no GS/OS application to hand off to, so quitting is a real one-way
// exit: this screen is drawn, and only the reset button brings the machine back.
//
// GS/OS's legacy text page turned out to be unusable from the game's native-mode exit path: the hardware
// reads the page back with an offset and a stride that do not match a plain 40x24 Apple II text page, and
// the soft switches that would change that have no effect.  So the message is rendered here, at build
// time, into Super Hi-Res pixels and the quit code copies it to the screen.  The glyphs come from the
// game's own CHR font (the same tiles the original credits screen uses), so the screen looks like it
// belongs to the game.
//
// Only the lines that carry text are emitted (eight pixel rows each, 160 bytes per row): the quit code
// clears the screen first, so the blank rows need no data, and the picture fits in MAIN instead of
// needing a ninth segment.
//
// Run: node scripts/make-quit-screen.mjs [--preview]
// Writes src/games/alterego/QuitScreen.s.
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const gameDir = join(here, '..', 'src', 'games', 'alterego');
const outPath = join(gameDir, 'QuitScreen.s');

const COLS = 40; // 320 px / 8 px per glyph
const ROWS = 25; // 200 px / 8 px per row
const CELL = 8;
const ROW_BYTES = 160; // 320 px * 4 bits / 2 bytes per word

// The game's font, as documented by scripts/gen-credits.py (the map the original credits screen uses).
// There is no glyph for Q or W, so the text avoids them.
const GLYPH = { ' ': 0x00 };
'ABCDEFGHIJKLMNOP'.split('').forEach((ch, i) => { GLYPH[ch] = 0x80 + i; });
'RSTUV'.split('').forEach((ch, i) => { GLYPH[ch] = 0x6b + i; });
GLYPH.X = 0x7b;
GLYPH.Y = 0x7c;
GLYPH.Z = 0x7d;
for (let d = 0; d < 10; d += 1) GLYPH[String(d)] = 0xf0 + d;

// Text row -> line.  Centred; a line occupies one 8-pixel row of the picture.
const LINES = [
    [5, 'ALTER EGO HAS EXITED'],
    [9, 'PRESS RESET TO PLAY AGAIN'],
    [14, 'THANKS FOR PLAYING'],
    [18, 'IT IS SAFE TO TURN OFF'],
];

const chr = readFileSync(join(gameDir, 'chr.bin'));
if (chr.length % 16) throw new Error(`chr.bin is not a whole number of tiles: ${chr.length}`);

// NES 2bpp tile -> 8 rows of 8 booleans (any non-zero pixel is ink).
const glyph = (code) => {
    const rows = [];
    const base = code * 16;
    for (let y = 0; y < 8; y += 1) {
        const p0 = chr[base + y];
        const p1 = chr[base + 8 + y];
        const row = [];
        for (let x = 7; x >= 0; x -= 1) row.push(((p0 >> x) & 1) || ((p1 >> x) & 1) ? 15 : 0);
        rows.push(row);
    }
    return rows;
};

// How the four pixels of a 16-bit word line up with the four screen pixels is a hardware detail, so it
// was not guessed: `--test` renders the same line in each of the four orders, one band per row, and the
// one that reads correctly is the one used.  Measured on the boot disk (GSplus): only `pairSwapped`
// reads as text, i.e. in memory a pixel pair occupies one byte with the leftmost pixel in the high
// nibble -- the two bytes of the word are the other way round from what `sta` of a 16-bit word writes.
const PACKS = {
    highNibble: (p) => (p[0] << 12) | (p[1] << 8) | (p[2] << 4) | p[3],
    lowNibble: (p) => (p[3] << 12) | (p[2] << 8) | (p[1] << 4) | p[0],
    byteSwap: (p) => (p[1] << 12) | (p[0] << 8) | (p[3] << 4) | p[2],
    pairSwapped: (p) => (p[2] << 12) | (p[3] << 8) | (p[0] << 4) | p[1],
};
const PACK = PACKS.pairSwapped;

// One 8-pixel band per line: 8 rows of 320 pixels packed four to a word, little-endian as the 65816
// stores it.
const band = (row, text, pack = PACK) => {
    if (text.length > COLS) throw new Error(`line too long for ${COLS} columns: ${text}`);
    const col = Math.max(0, Math.floor((COLS - text.length) / 2));
    const pixels = Array.from({ length: CELL }, () => new Array(COLS * CELL).fill(0));
    [...text].forEach((ch, i) => {
        const code = GLYPH[ch];
        if (code === undefined) throw new Error(`no glyph for ${JSON.stringify(ch)} in ${JSON.stringify(text)}`);
        const g = glyph(code);
        for (let y = 0; y < CELL; y += 1) {
            for (let x = 0; x < CELL; x += 1) pixels[y][(col + i) * CELL + x] = g[y][x];
        }
    });
    const bytes = [];
    for (let y = 0; y < CELL; y += 1) {
        for (let x = 0; x < COLS * CELL; x += 4) {
            const word = pack([pixels[y][x], pixels[y][x + 1], pixels[y][x + 2], pixels[y][x + 3]]);
            bytes.push(word & 0xff, (word >> 8) & 0xff);
        }
        if (pixels[y].length && bytes.length % ROW_BYTES) throw new Error('row is not a whole number of words');
    }
    if (bytes.length !== CELL * ROW_BYTES) throw new Error(`band is ${bytes.length} bytes, expected ${CELL * ROW_BYTES}`);
    return { row, text, bytes };
};

// `--test` puts the four candidate orders on the four rows the quit code copies, so one boot says which
// one the hardware wants: the row that reads correctly names the winner.
const testMode = process.argv.includes('--test');
const bands = testMode
    ? ['highNibble', 'lowNibble', 'byteSwap', 'pairSwapped'].map((name, i) => {
        const [row, text] = LINES[i];
        return { ...band(row, text, PACKS[name]), text: `${name}: ${text}` };
    })
    : LINES.map(([row, text]) => band(row, text));

const hex2 = (v) => '$' + v.toString(16).toUpperCase().padStart(2, '0');
const out = [
    '; The quit screen: four bands of eight Super Hi-Res rows, the lines of the message.',
    '; Generated by scripts/make-quit-screen.mjs -- do not edit by hand.',
    '; Each band is 160 bytes per row, four pixels per 16-bit word, leftmost pixel in the high nibble;',
    '; pixel 0 is the background and pixel 15 the ink (the quit code loads those two palette entries).',
    '; Main.s clears the screen and copies each band to the row it belongs to.',
];
bands.forEach(({ row, text, bytes }, i) => {
    out.push('', `; pixel row ${row * CELL} (text row ${row}): ${text}`);
    out.push(`quitBand${i}`);
    for (let at = 0; at < bytes.length; at += 16) {
        out.push(`            dfb   ${bytes.slice(at, at + 16).map(hex2).join(',')}`);
    }
});
out.push('');
writeFileSync(outPath, out.join('\n'));
console.log(`  quit screen .. QuitScreen.s (${bands.length} bands, ${bands[0].bytes.length} bytes each)`);

if (process.argv.includes('--preview')) {
    // Decode the bytes the way the hardware reads them: one byte holds two pixels, leftmost in the high
    // nibble, and the two bytes of a word are [pixels 0,1] then [pixels 2,3].
    const preview = [];
    const screen = Array.from({ length: ROWS * CELL }, () => new Array(COLS * CELL).fill(0));
    bands.forEach(({ row, bytes }) => {
        for (let y = 0; y < CELL; y += 1) {
            for (let x = 0; x < COLS * CELL; x += 4) {
                const at = y * ROW_BYTES + (x >> 2) * 2;
                screen[row * CELL + y][x] = bytes[at] >> 4 ? 15 : 0;
                screen[row * CELL + y][x + 1] = bytes[at] & 0xf ? 15 : 0;
                screen[row * CELL + y][x + 2] = bytes[at + 1] >> 4 ? 15 : 0;
                screen[row * CELL + y][x + 3] = bytes[at + 1] & 0xf ? 15 : 0;
            }
        }
    });
    for (let y = 0; y < ROWS * CELL; y += 4) {
        let line = '';
        for (let x = 0; x < COLS * CELL; x += 4) {
            let n = 0;
            for (let dy = 0; dy < 4; dy += 1) for (let dx = 0; dx < 4; dx += 1) n += screen[y + dy][x + dx] ? 1 : 0;
            line += n === 0 ? ' ' : n < 5 ? '.' : n < 10 ? '+' : '#';
        }
        preview.push(line);
    }
    console.log(preview.join('\n'));
}
