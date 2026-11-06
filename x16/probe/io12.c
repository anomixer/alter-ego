/* x16/probe/io12.c - does KERNAL LOAD write directly into VERA VRAM? */
#include <stdio.h>
#include <cbm.h>
#include <cx16.h>

unsigned char ae_flag;
unsigned ae_addr;
unsigned ae_end;
unsigned char ae_err;
unsigned char ae_status;

extern void ae_kload (void);

static unsigned char rdb[4];

static void rd (unsigned long va)
{
    VERA.address = va;
    rdb[0] = VERA.data0;
    rdb[1] = VERA.data0;
    rdb[2] = VERA.data0;
    rdb[3] = VERA.data0;
}

static void try (const char *name, unsigned char sa, unsigned char flag, unsigned addr)
{
    ae_flag = flag;
    ae_addr = addr;
    cbm_k_setnam (name);
    cbm_k_setlfs (2, 8, sa);
    ae_kload ();
    printf ("%s f=%d sa=%d err=%02X P=%02X\n", name, flag, sa, ae_err, ae_status);
}

int main (void)
{
    printf ("IO12\n");

    try ("LV00", 2, 2, 0x0000);
    rd (0x00000UL);
    printf ("vram0000 %02X %02X %02X %02X (98 05 9E 00)\n", rdb[0], rdb[1], rdb[2], rdb[3]);

    try ("CRPAL", 2, 2, 0x2000);
    rd (0x02000UL);
    printf ("vram2000 %02X %02X %02X %02X (00 00 07 00)\n", rdb[0], rdb[1], rdb[2], rdb[3]);

    try ("TILES", 2, 3, 0x0000);
    rd (0x10000UL);
    printf ("vram10000 %02X %02X %02X %02X (00 00 00 00)\n", rdb[0], rdb[1], rdb[2], rdb[3]);
    rd (0x103E8UL);
    printf ("vram103E8 %02X %02X %02X %02X (33 33 33 33)\n", rdb[0], rdb[1], rdb[2], rdb[3]);
    rd (0x003E8UL);
    printf ("vram003E8 %02X %02X %02X %02X\n", rdb[0], rdb[1], rdb[2], rdb[3]);

    printf ("DONE\n");
    return 0;
}
