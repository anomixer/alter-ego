/* x16/probe/io.c - does cc65's POSIX open/read work on the X16 with HostFS? */
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

static unsigned char buf[32];

int main(void)
{
    static const char *names[4] = { "TILES", "CREDITS", "CRPAL", "LV00" };
    int i, j;

    printf("IO PROBE\n");
    for (i = 0; i < 4; ++i) {
        int fd = open(names[i], O_RDONLY);
        int n = -1;
        if (fd >= 0) {
            n = read(fd, buf, 16);
            close(fd);
        }
        printf("%s fd=%d n=%d\n", names[i], fd, n);
        if (n > 0) {
            for (j = 0; j < 4; ++j) printf("%02X ", buf[j]);
            printf("\n");
        }
    }
    printf("DONE\n");
    return 0;
}
