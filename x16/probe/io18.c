/* x16/probe/io18.c - KERNAL LOAD with A=3 into VRAM bank 1, correct A16 handling. */
#include <stdio.h>
#include <cbm.h>
#include <cx16.h>

unsigned char ae_flag;
unsigned ae_addr;
unsigned ae_end;
unsigned char ae_err;
unsigned char ae_status;

extern void ae_kload (void);

static void dump_vram (const char *tag, unsigned long addr)
{
    int i;
    VERA.address = (unsigned) (addr & 0xFFFF);
    VERA.address_hi = (unsigned char) (0x10 | ((addr >> 16) & 1));
    printf ("%s ", tag);
    for (i = 0; i < 8; ++i) printf ("%02X ", VERA.data0);
    printf ("\n");
}

int main (void)
{
    printf ("IO18\n");
    ae_flag = 3;
    ae_addr = 0x0000;
    cbm_k_setnam ("TILES");
    cbm_k_setlfs (2, 8, 2);
    ae_kload ();
    printf ("TILES f=3 a=0 err=%02X P=%02X\n", ae_err, ae_status);
    dump_vram ("b1 10000+1000", 0x10000UL + 1000);
    dump_vram ("b1 10000+0", 0x10000UL);
    dump_vram ("b0 00000+1000", 0x00000UL + 1000);
    printf ("DONE\n");
    return 0;
}
