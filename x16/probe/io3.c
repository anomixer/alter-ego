/* x16/probe/io3.c - direct KERNAL OPEN/CHKIN/CHRIN, bypassing cc65 open(). */
#include <stdio.h>
#include <cbm.h>

int main(void)
{
    unsigned char st;
    int i;

    printf("IO3\n");

    cbm_k_setnam("TILES");
    cbm_k_setlfs(2, 8, 0);          /* LFN 2, device 8, SA 0 */
    st = cbm_k_open();
    printf("kopen A=%d st=%d\n", st, cbm_k_readst());

    cbm_k_chkin(2);
    printf("chkin st=%d\n", cbm_k_readst());
    for (i = 0; i < 4; ++i) {
        unsigned char c = cbm_k_chrin();
        printf("%02X ", c);
    }
    printf("\n");
    cbm_k_close(2);
    printf("DONE\n");
    return 0;
}
