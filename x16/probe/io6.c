/* x16/probe/io6.c - CHRIN/READST without printing inside the loop. */
#include <stdio.h>
#include <cbm.h>

static unsigned char buf[8];
static unsigned char sts[8];

int main(void)
{
    unsigned char st;
    int i;

    printf("IO6\n");
    cbm_k_setnam ("TILES");
    cbm_k_setlfs (2, 8, 0);
    st = cbm_k_open ();
    printf("open A=%d\n", st);
    cbm_k_chkin (2);
    for (i = 0; i < 8; ++i) {
        buf[i] = cbm_k_chrin ();
        sts[i] = cbm_k_readst ();
    }
    cbm_k_close (2);
    for (i = 0; i < 8; ++i) {
        printf("%d=%02X/%02X ", i, buf[i], sts[i]);
    }
    printf("\nDONE\n");
    return 0;
}
