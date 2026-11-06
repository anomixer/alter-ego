/* x16/probe/io5.c - is the __fastcall__ word argument arriving intact? */
#include <stdio.h>
#include <cbm.h>

static unsigned char buf[32];

int __fastcall__ myread (int fd, void *bufp, unsigned count)
{
    unsigned i;
    unsigned char *p = (unsigned char *) bufp;

    printf("myread fd=%d count=%u\n", fd, count);
    cbm_k_chkin ((unsigned char) fd);
    for (i = 0; i < count; ++i) {
        unsigned char st = cbm_k_readst ();
        unsigned char c = cbm_k_chrin ();
        p[i] = c;
        printf("%d: %02X st=%02X\n", i, c, st);
        if (i >= 5) break;
    }
    return (int) i;
}

int main(void)
{
    unsigned char st;
    printf("IO5\n");
    cbm_k_setnam ("TILES");
    cbm_k_setlfs (2, 8, 0);
    st = cbm_k_open ();
    printf("open A=%d st=%02X\n", st, cbm_k_readst ());
    myread (2, buf, 16);
    cbm_k_close (2);
    printf("DONE\n");
    return 0;
}
