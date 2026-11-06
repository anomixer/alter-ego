/* x16/probe/io11.c - the documented OPEN form: SA=2 with ",S,R" in the name. */
#include <stdio.h>
#include <cbm.h>

static unsigned char buf[8];
static unsigned char sts[8];

static void attempt (const char *name, unsigned char sa, int count)
{
    unsigned char st;
    int i;

    cbm_k_setnam (name);
    cbm_k_setlfs (4, 8, sa);
    st = cbm_k_open ();
    cbm_k_chkin (4);
    for (i = 0; i < count; ++i) {
        buf[i] = cbm_k_chrin ();
        sts[i] = cbm_k_readst ();
    }
    cbm_k_close (4);
    printf ("[%s] sa=%d A=%d ", name, sa, st);
    for (i = 0; i < count; ++i) printf ("%02X/%02X ", buf[i], sts[i]);
    printf ("\n");
}

int main (void)
{
    printf ("IO11\n");
    attempt ("TILES,S,R", 2, 4);
    attempt ("TILES,S,R", 0, 4);
    attempt ("TILES,S", 2, 4);
    attempt ("TILES,S,R", 2, 4);
    printf ("DONE\n");
    return 0;
}
