/* x16/probe/io14.c - flag=3 at a non-zero address, and the 2-byte-header path. */
#include <stdio.h>
#include <cbm.h>
#include <cx16.h>

unsigned char ae_flag;
unsigned ae_addr;
unsigned ae_end;
unsigned char ae_err;
unsigned char ae_status;

extern void ae_kload (void);

static unsigned char rdb[8];

static void dump (const char *tag, unsigned long va)
{
    int i;
    VERA.address = va;
    for (i = 0; i < 8; ++i) rdb[i] = VERA.data0;
    printf ("%s ", tag);
    for (i = 0; i < 8; ++i) printf ("%02X ", rdb[i]);
    printf ("\n");
}

static void try (const char *name, unsigned char sa, unsigned char flag, unsigned addr)
{
    ae_flag = flag;
    ae_addr = addr;
    cbm_k_setnam (name);
    cbm_k_setlfs (2, 8, sa);
    ae_kload ();
    printf ("%s f=%d sa=%d addr=%u err=%02X P=%02X\n", name, flag, sa, addr, ae_err, ae_status);
}

int main (void)
{
    printf ("IO14\n");
    try ("TILES", 2, 3, 0x2000);
    dump ("vram123E8", 0x123E8UL);
    try ("TILESH", 1, 3, 0x0000);
    dump ("vram103E8", 0x103E8UL);
    printf ("DONE\n");
    return 0;
}
