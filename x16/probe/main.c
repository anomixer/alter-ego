/*
 * x16/probe/main.c - Commander X16 VERA bring-up probe for the alter-ego port
 *
 * Draws the exact display the Apple II + VERA port needs (320x240, one 4bpp
 * tile layer, 64x32 map, 8x8 tiles) plus one sprite, and animates it with the
 * VERA VSYNC counter.  Written only against cc65's <cx16.h> VERA struct, i.e.
 * the same registers the a2vera sources touch at slot base + 0x00..0x11.
 *
 * Build: cl65 -t cx16 -O -o vera_probe.prg main.c
 * Run:   x16emu.exe -prg vera_probe.prg -run
 */

#include <cx16.h>
#include <time.h>

#define VRAM_TILES 0x10000UL /* 512 x 32-byte 4bpp tiles */
#define VRAM_SPR   0x14000UL /* sprite image */
#define VRAM_MAP   0x18000UL /* 64 x 32 x 2-byte map */
#define MAP_W      64

static void vram_seek (unsigned long addr)
{
    VERA.address = (unsigned short)addr;
    VERA.address_hi = (unsigned char)(addr >> 16) | 0x10; /* increment 1 */
}

static void vram_put (unsigned char value)
{
    VERA.data0 = value;
}

/* 2 bytes per palette entry: GGBBBBBB, ----RRRR */
static void set_color (unsigned char index, unsigned char r,
                       unsigned char g, unsigned char b)
{
    vram_seek (0x1FA00UL + index * 2UL);
    vram_put ((unsigned char)((g << 4) | b));
    vram_put (r);
}

int main (void)
{
    unsigned int  i;
    unsigned char x, y, t;
    unsigned char frame = 0;

    /* 1. palette: 16 colours, the same shape the a2vera palette tables use */
    for (i = 0; i < 16; ++i)
        set_color (i, (unsigned char)((i & 1) ? 15 : 0), (unsigned char)((i & 2) ? 15 : 0),
                   (unsigned char)((i & 4) ? 15 : 0));

    set_color (0, 0, 0, 0);      /* transparent / black */
    set_color (1, 15, 0, 0);     /* red */
    set_color (2, 0, 15, 0);     /* green */
    set_color (3, 15, 15, 0);    /* yellow */
    set_color (4, 0, 0, 15);     /* blue */
    set_color (5, 15, 0, 15);    /* magenta */
    set_color (6, 0, 15, 15);    /* cyan */
    set_color (7, 15, 15, 15);   /* white */

    /* 2. tiles: tile n is a solid 8x8 block of colour n (32 bytes, 4bpp) */
    vram_seek (VRAM_TILES);
    for (t = 0; t < 16; ++t) {
        for (i = 0; i < 32; ++i) {
            unsigned char px = t;
            vram_put ((unsigned char)((px << 4) | px));
        }
    }

    /* 3. map: 4-tile-wide colour bands, 4bpp, no flips/palette offset */
    vram_seek (VRAM_MAP);
    for (y = 0; y < 32; ++y) {
        for (x = 0; x < MAP_W; ++x) {
            vram_put ((unsigned char)(((x >> 2) + (y >> 2)) & 15));
            vram_put (0);
        }
    }

    /* 4. layer 0: 64x32 map, 4bpp, 8x8 tiles, both layers off */
    VERA.layer0.config    = 0b00010010; /* 64 wide, 32 high, 4bpp */
    VERA.layer0.mapbase   = (unsigned char)(VRAM_MAP >> 9);
    VERA.layer0.tilebase  = (unsigned char)(VRAM_TILES >> 9);
    VERA.layer0.hscroll   = 0;
    VERA.layer0.vscroll   = 0;

    /* 5. one 8x8 4bpp sprite above the tiles */
    vram_seek (VRAM_SPR);
    for (i = 0; i < 32; ++i)
        vram_put ((unsigned char)(0x77 ^ (unsigned char)i));

    vram_seek (0x1FC00UL);
    vram_put ((unsigned char)(VRAM_SPR >> 5));           /* addr 12:5 */
    vram_put ((unsigned char)(VRAM_SPR >> 13));          /* mode 0 (4bpp) + addr 16:13 */
    vram_put (160);                                      /* x */
    vram_put (0);
    vram_put (120);                                      /* y */
    vram_put (0);
    vram_put (0b00001100);                               /* z-depth 3, no flips */
    vram_put (0b00000000);                               /* 8x8, palette offset 0 */

    /* 6. 320x240: half-scale the 640x480 active area; DC_VIDEO bits are
     *    [6]=sprites [5]=layer1 [4]=layer0, so turn the KERNAL text layer off */
    VERA.display.hscale = 64;
    VERA.display.vscale = 64;
    VERA.display.video &= (unsigned char)~0x20; /* layer 1 (text) off */
    VERA.display.video |= 0x40 | 0x10;           /* sprites + layer 0 on */

    /* 7. PSG voice 0: 440 Hz triangle on both channels (audio path check) */
    vram_seek (0x1F9C0UL);
    vram_put (1181 & 0xFF);
    vram_put (1181 >> 8);
    vram_put (0b11000000 | 0x30); /* L+R, volume 48 */
    vram_put (0b10000000 | 0x3F); /* triangle, full pulse width */

    /* 8. animate: scroll the layer and move the sprite, one step per VSYNC.
     *    USE_ISR=1 reproduces the a2vera frame-pacing idiom (poll VERA ISR
     *    bit 0); the default uses the KERNAL 60 Hz jiffy clock instead. */
    for (;;) {
#ifdef USE_ISR
        while (!(VERA.irq_flags & 0x01))
            ;
        VERA.irq_flags = 0x01;
#else
        unsigned long tick = clock ();
        while (clock () == tick)
            ;
#endif
        ++frame;
        VERA.layer0.hscroll = (unsigned int)(frame * 2);
        vram_seek (0x1FC02UL);          /* sprite x */
        vram_put ((unsigned char)(96 + (frame & 63)));
        vram_put (0);
    }
    return 0;
}
