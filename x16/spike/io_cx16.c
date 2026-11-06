/* x16/spike/io_cx16.c - level-file API for the X16 build.
 *
 * Files are staged in VRAM by asset_cx16.c (KERNAL LOAD A=2), then streamed
 * back byte by byte through the VERA data port.  cc65's own CBM layer is not
 * usable here: open() always fails on HostFS.
 */
#include <cbm.h>
#include <fcntl.h>
#include <unistd.h>
#include <cx16.h>

extern void ae_stage_vram (const char *name);
extern unsigned char ae_read_stage (unsigned long pos);

#define AE_MAX_LFN 15

#ifdef AE_DEBUG
/* x16emu "User debug 1" beacon ($9FB9); the trace file shows the call order. */
static void dbg (unsigned char c) { *(volatile unsigned char *) 0x9FB9 = c; }
#else
#define dbg(c) ((void) 0)
#endif

static unsigned char fd_used[AE_MAX_LFN + 1];
static unsigned long fd_pos[AE_MAX_LFN + 1];

int open (const char *name, int flags, ...)
{
    unsigned char lfn;

    (void) flags;
    for (lfn = 2; lfn <= AE_MAX_LFN; ++lfn) {
        if (!fd_used[lfn]) break;
    }
    if (lfn > AE_MAX_LFN) return -1;
    dbg ('o');
    ae_stage_vram (name);
    dbg ('O');
    fd_used[lfn] = 1;
    fd_pos[lfn] = 0;
    return (int) lfn;
}

int __fastcall__ read (int fd, void *buf, unsigned count)
{
    unsigned i;
    unsigned char *p = (unsigned char *) buf;
    unsigned long pos;
    unsigned saved_addr;
    unsigned char saved_hi;

    if (fd < 0 || fd > AE_MAX_LFN || !fd_used[fd]) return -1;
    /* Streaming from the VRAM staging area needs the VERA address registers,
     * but the caller keeps its own destination address in them (the level
     * loader writes the map through DATA0 between reads).  Save and restore
     * the pair around the transfer so the caller's pointer survives. */
    saved_addr = VERA.address;
    saved_hi = VERA.address_hi;
    pos = fd_pos[fd];
    for (i = 0; i < count; ++i) p[i] = ae_read_stage (pos + i);
    fd_pos[fd] = pos + count;
    VERA.address = saved_addr;
    VERA.address_hi = saved_hi;
    return (int) count;
}

int __fastcall__ close (int fd)
{
    if (fd < 0 || fd > AE_MAX_LFN || !fd_used[fd]) return -1;
    fd_used[fd] = 0;
    return 0;
}
