/* x16/probe/io8.c - KERNAL LOAD straight into VERA VRAM (A=3). */
#include <stdio.h>
#include <cbm.h>
#include <cx16.h>

int main (void)
{
    unsigned end;
    unsigned char a, b, c, d;

    printf ("IO8\n");

    cbm_k_setnam ("TILES");
    cbm_k_setlfs (2, 8, 2);          /* headerless: load the whole file */
    end = cbm_k_load (3, 0);         /* A=3 -> VRAM $10000 + addr */
    printf ("end=%u st=%02X\n", end, cbm_k_readst ());

    VERA.address = 0x11000UL + 1000; /* $10000 | A16 set in the high byte */
    a = VERA.data0;
    b = VERA.data0;
    c = VERA.data0;
    d = VERA.data0;
    printf ("vram %02X %02X %02X %02X\n", a, b, c, d);

    printf ("DONE\n");
    return 0;
}
