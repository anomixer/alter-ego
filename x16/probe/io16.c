/* x16/probe/io16.c - KERNAL LOAD: VRAM (A=2) vs banked RAM (A=0), TILES vs TILES0 */
#include <stdio.h>
#include <cbm.h>
#include <cx16.h>

unsigned char ae_flag;
unsigned ae_addr;
unsigned ae_end;
unsigned char ae_err;
unsigned char ae_status;

extern void ae_kload (void);

static void dump_ram (const char *tag, unsigned char bank, unsigned addr)
{
    int i;
    RAM_BANK = bank;
    printf ("%s ", tag);
    for (i = 0; i < 8; ++i) printf ("%02X ", *(volatile unsigned char *) (addr + i));
    printf ("\n");
}

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
    printf ("IO16\n");
    RAM_BANK = 1;
    load ("TILES", 2, 0x8000);
    dump_vram ("TILES  v8000+1000", 0x08000UL + 1000);
    load ("TILES0", 2, 0x8000);
    dump_vram ("TILES0 v8000+4096", 0x08000UL + 4096);
    load ("TILES0", 0, 0xA000);
    dump_ram ("TILES0 b1 A000+4096", 1, 0xB000);
    dump_ram ("TILES0 b1 A000+0", 1, 0xA000);
    printf ("DONE\n");
    return 0;
}
