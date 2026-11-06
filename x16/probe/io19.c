/* x16/probe/io19.c - the three load cases the port needs. */
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

static void load (const char *name, unsigned char flag, unsigned addr)
{
    ae_flag = flag;
    ae_addr = addr;
    cbm_k_setnam (name);
    cbm_k_setlfs (2, 8, 2);
    ae_kload ();
    printf ("%s f=%u a=%u err=%02X P=%02X\n", name, flag, addr, ae_err, ae_status);
}

int main (void)
{
    printf ("IO19\n");
    load ("CRPAL", 3, 0xFA00);
    dump_vram ("palette 1FA00", 0x1FA00UL);
    load ("LV00", 2, 0xA000);
    dump_vram ("scratch A000", 0xA000UL);
    load ("GOVER", 2, 0x0000);
    dump_vram ("map 00000", 0x00000UL);
    printf ("DONE\n");
    return 0;
}
