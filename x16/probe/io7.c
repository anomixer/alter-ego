/* x16/probe/io7.c - which OPEN form yields readable data under HostFS? */
#include <stdio.h>
#include <cbm.h>

static unsigned char buf[4];
static unsigned char sts[4];

static void attempt (const char *name, unsigned char sa)
{
    unsigned char st;
    unsigned char a, b;
    unsigned char s0, s1;
    int i;

    cbm_k_setnam (name);
    cbm_k_setlfs (3, 8, sa);
    st = cbm_k_open ();
    cbm_k_chkin (3);
    a = cbm_k_chrin ();
    s0 = cbm_k_readst ();
    b = cbm_k_chrin ();
    s1 = cbm_k_readst ();
    cbm_k_close (3);
    printf ("[%s] sa=%d A=%d %02X/%02X %02X/%02X\n", name, sa, st, a, s0, b, s1);
    (void) i;
    (void) buf;
    (void) sts;
}

int main (void)
{
    printf ("IO7\n");
    attempt ("TILES", 0);
    attempt ("TILES,S,R", 0);
    attempt ("TILES", 2);
    attempt ("TILES", 1);
    printf ("DONE\n");
    return 0;
}
