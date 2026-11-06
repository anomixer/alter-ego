/* x16/probe/io20.c - does writing the VERA address registers drift the address? */
#include <stdio.h>
#include <cx16.h>

static void seta (unsigned long a)
{
    VERA.address = (unsigned) (a & 0xFFFF);
    VERA.address_hi = (unsigned char) (0x10 | ((a >> 16) & 1));
}

int main (void)
{
    unsigned char i;
    unsigned char b[8];

    printf ("IO20\n");

    seta (0x1FA00UL);
    for (i = 0; i < 8; ++i) VERA.data0 = (unsigned char) (0x11 + i);

    seta (0x1FA00UL);
    for (i = 0; i < 8; ++i) b[i] = VERA.data0;

    printf ("read ");
    for (i = 0; i < 8; ++i) printf ("%02X ", b[i]);
    printf ("\n");

    /* second round: two consecutive address setups */
    seta (0x1FA08UL);
    for (i = 0; i < 4; ++i) VERA.data0 = (unsigned char) (0xA1 + i);
    seta (0x1FA08UL);
    for (i = 0; i < 4; ++i) b[i] = VERA.data0;
    printf ("read2 ");
    for (i = 0; i < 4; ++i) printf ("%02X ", b[i]);
    printf ("\nDONE\n");
    return 0;
}
