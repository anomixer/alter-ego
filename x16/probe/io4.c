/* x16/probe/io4.c - exercise the same streaming pattern the game uses. */
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

static unsigned char buf[512];

static void stream(const char *name, unsigned size)
{
    int fd = open(name, O_RDONLY);
    unsigned done = 0;
    int chunks = 0;
    if (fd < 0) { printf("%s OPEN FAIL\n", name); return; }
    while (done < size) {
        unsigned want = size - done;
        int n;
        if (want > sizeof(buf)) want = sizeof(buf);
        n = read(fd, buf, want);
        printf("chunk %d n=%d\n", chunks++, n);
        if (n <= 0) break;
        done += (unsigned) n;
        if (chunks > 40) { printf("TOO MANY\n"); break; }
    }
    close(fd);
    printf("%s done=%u\n", name, done);
}

int main(void)
{
    printf("IO4\n");
    stream("CREDITS", 4096);
    stream("TILES", 16384);
    printf("DONE\n");
    return 0;
}
