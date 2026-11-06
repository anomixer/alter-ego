/* x16/probe/io9.c - LOAD matrix: RAM vs VRAM, SA 0/1/2. */
#include <stdio.h>
#include <cbm.h>
#include <cx16.h>

static unsigned char peek (unsigned long vaddr)
{
    VERA.address = vaddr;
    return VERA.data0;
}

static void attempt (const char *name, unsigned char flag, unsigned char sa,
                     unsigned addr, unsigned long vaddr)
{
    unsigned end;
    unsigned char st;
    unsigned char a, b;

    cbm_k_setnam (name);
    cbm_k_setlfs (2, 8, sa);
    end = cbm_k_load (flag, addr);
    st = cbm_k_readst ();
    a = peek (vaddr);
    b = peek (vaddr + 1);
    printf ("%s f=%d sa=%d addr=%u end=%u st=%02X vr=%02X %02X\n",
            name, flag, sa, addr, end, st, a, b);
}

int main (void)
{
    printf ("IO9\n");
    attempt ("LV00", 0, 0, 0x0400, 0x10400UL);
    attempt ("LV00", 0, 2, 0x0400, 0x10400UL);
    attempt ("LV00", 0, 1, 0x0400, 0x10400UL);
    attempt ("TILES", 3, 0, 0x0000, 0x11000UL + 1000);
    attempt ("TILES", 3, 2, 0x0000, 0x11000UL + 1000);
    attempt ("CREDITS", 2, 2, 0x2000, 0x12000UL);
    printf ("DONE\n");
    return 0;
}
