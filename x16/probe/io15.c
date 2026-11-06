/* x16/probe/io15.c - does LOAD of a 16 KB file auto-advance banked RAM banks? */
#include <stdio.h>
#include <cbm.h>
#include <cx16.h>

unsigned char ae_flag;
unsigned ae_addr;
unsigned ae_end;
unsigned char ae_err;
unsigned char ae_status;

extern void ae_kload (void);

static void dump (const char *tag, unsigned char bank, unsigned addr)
{
    int i;
    RAM_BANK = bank;
    printf ("%s ", tag);
    for (i = 0; i < 8; ++i) printf ("%02X ", *(volatile unsigned char *) (addr + i));
    printf ("\n");
}

int main (void)
{
    printf ("IO15\n");
    RAM_BANK = 1;
    ae_flag = 0;
    ae_addr = 0xA000;
    cbm_k_setnam ("TILES");
    cbm_k_setlfs (2, 8, 2);
    ae_kload ();
    printf ("err=%02X P=%02X\n", ae_err, ae_status);
    dump ("b1@A000", 1, 0xA000);
    dump ("b1@B000", 1, 0xB000);
    dump ("b2@A000", 2, 0xA000);
    dump ("b3@A000", 3, 0xA000);
    RAM_BANK = 1;
    printf ("DONE\n");
    return 0;
}
