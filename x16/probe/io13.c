/* x16/probe/io13.c - LOAD into VRAM at non-zero addresses. */
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

static void rd (unsigned long va)
{
    int i;
    VERA.address = va;
    for (i = 0; i < 8; ++i) rdb[i] = VERA.data0;
}

static void dump (const char *tag, unsigned long va)
{
    int i;
    rd (va);
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
    printf ("IO13\n");
    try ("LV00", 2, 2, 0x4000);
    dump ("vram4000", 0x04000UL);
    try ("TILES", 2, 2, 0x8000);
    dump ("vram83E8", 0x083E8UL);
    dump ("vram8000", 0x08000UL);
    printf ("DONE\n");
    return 0;
}
