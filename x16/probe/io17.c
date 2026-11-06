/* x16/probe/io17.c - does a headered (SA=1) LOAD land at $A000? */
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

int main (void)
{
    printf ("IO17\n");
    RAM_BANK = 1;
    ae_flag = 0;
    ae_addr = 0xA000;
    cbm_k_setnam ("LV00L");
    cbm_k_setlfs (2, 8, 1);
    ae_kload ();
    printf ("err=%02X P=%02X end=%u\n", ae_err, ae_status, ae_end);
    dump_ram ("b1 A000", 1, 0xA000);
    printf ("DONE\n");
    return 0;
}
