/* x16/probe/io10.c - asm KERNAL LOAD, RAM and VRAM, using loader.s conventions. */
#include <stdio.h>
#include <cbm.h>
#include <cx16.h>

unsigned char ae_flag;
unsigned ae_addr;
unsigned ae_end;
unsigned char ae_err;
unsigned char ae_status;

extern void ae_kload (void);

static void try (const char *name, unsigned char sa, unsigned char flag, unsigned addr)
{
    ae_flag = flag;
    ae_addr = addr;
    ae_end = 0xEEEE;
    ae_err = 0xEE;
    cbm_k_setnam (name);
    cbm_k_setlfs (2, 8, sa);
    ae_kload ();
    printf ("%s f=%d sa=%d end=%u err=%02X P=%02X\n", name, flag, sa, ae_end, ae_err, ae_status);
}

int main (void)
{
    unsigned char a, b, c, d;

    printf ("IO10\n");

    RAM_BANK = 1;
    try ("LV00", 2, 0, 0xA000);
    a = *(volatile unsigned char *) 0xA000;
    b = *(volatile unsigned char *) 0xA001;
    c = *(volatile unsigned char *) 0xA002;
    d = *(volatile unsigned char *) 0xA003;
    printf ("ram %02X %02X %02X %02X\n", a, b, c, d);

    try ("TILES", 2, 3, 0x0000);
    VERA.address = 0x10000UL + 1000;
    a = VERA.data0; b = VERA.data0; c = VERA.data0; d = VERA.data0;
    printf ("vram %02X %02X %02X %02X\n", a, b, c, d);
    printf ("DONE\n");
    return 0;
}
