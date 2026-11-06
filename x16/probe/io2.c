/* x16/probe/io2.c - which filename form does cc65's open() accept on X16? */
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

static unsigned char buf[8];

static void try(const char *name)
{
    int fd = open(name, O_RDONLY);
    int n = -1;
    if (fd >= 0) {
        n = read(fd, buf, 4);
        close(fd);
    }
    printf("[%s] fd=%d n=%d\n", name, fd, n);
    if (n > 0) printf("  %02X %02X %02X %02X\n", buf[0], buf[1], buf[2], buf[3]);
}

int main(void)
{
    printf("IO2\n");
    try("TILES");
    try("8:TILES");
    try("TILES,S,R");
    try("//TILES");
    try("LV00");
    printf("DONE\n");
    return 0;
}
