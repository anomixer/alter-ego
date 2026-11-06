/* x16/probe/io21.c - can a standalone program LOAD the 29 KB GAME file? */
#include <stdio.h>
#include <cbm.h>

unsigned char ae_flag;
unsigned ae_addr;
unsigned ae_end;
unsigned char ae_err;
unsigned char ae_status;

extern void ae_kload (void);

static void mark (unsigned char c) { *(volatile unsigned char *) 0x9FB9 = c; }

int main (void)
{
    mark ('1');
    ae_flag = 0;
    ae_addr = 0;
    cbm_k_setnam ("GAME");
    cbm_k_setlfs (1, 8, 1);
    ae_kload ();
    mark ('2');
    printf ("GAME err=%02X P=%02X\n", ae_err, ae_status);
    printf ("at 2000: %02X %02X\n", *(unsigned char *) 0x2000, *(unsigned char *) 0x2001);
    mark ('3');
    return 0;
}
