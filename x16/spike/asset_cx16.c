/* x16/spike/asset_cx16.c - KERNAL LOAD asset layer for the X16 build.
 *
 * Verified against x16emu r49 HostFS (see x16/spike/t3.s, t5.s, t8.s):
 *   - HostFS resolves names by their exact byte sequence: a SETNAM name in
 *     upper case returns FILE NOT FOUND (A=4), while the same name in lower
 *     case loads correctly.  ae_load() therefore lower-cases every name.
 *   - A=2 loads into VRAM bank 0 at X/Y, A=3 loads into VRAM bank 1 at X/Y.
 *   - Address $0000 cannot be loaded to directly, so bank-0 assets that live
 *     at 0 are staged at $A000 and copied down.
 *   - KERNAL LOAD returns carry set even on success, so the status byte is
 *     not used either; the callers verify by reading the target back.
 */
#include <cbm.h>
#include <cx16.h>

unsigned char ae_flag;
unsigned ae_addr;
unsigned ae_end;
unsigned char ae_err;
unsigned char ae_status;

#ifdef AE_X16_AUTOSTART
/* Test-only: -DAE_X16_AUTOSTART=<level> makes the title menu jump straight
 * into that level, so automated x16emu captures can reach gameplay without a
 * keyboard.  Absent from every normal build. */
unsigned char ae_autostart_level = AE_X16_AUTOSTART;
#endif

extern void ae_kload (void);
extern void ae_clrchn (void);   /* CLRCHN wrapper in clrchn_cx16.s */

#define AE_STAGE 0xA000UL          /* free VRAM (bank 0) scratch area */

/* Copy an asset name into a private buffer, lower-cased for HostFS. */
static void ae_lname (char *dst, const char *src)
{
    unsigned char i = 0;

    while (src[i] && i < 15) {
        char c = src[i];
        if (c >= 'A' && c <= 'Z') c = (char) (c + ('a' - 'A'));
        dst[i] = c;
        ++i;
    }
    dst[i] = 0;
}

static void dbg (unsigned char c)
{
    *(volatile unsigned char *) 0x9FB9 = c;   /* x16emu "User debug 1" */
}

static void vera_addr (unsigned long a)
{
    VERA.address = (unsigned) (a & 0xFFFF);
    /* bits 6-4 select the auto-increment (1 here), bit 0 is address bit 16. */
    VERA.address_hi = (unsigned char) (0x10 | ((a >> 16) & 0x01));
}

static unsigned char ae_load (const char *name, unsigned char flag, unsigned addr)
{
    unsigned char oldien = VERA.irq_enable;
    unsigned char st;
    char lname[16];

    /* An IRQ in the middle of KERNAL LOAD wrecks the transfer, so mask
     * interrupts; HostFS also wants the banked-RAM window away from the DOS
     * buffers. */
    VERA.irq_enable = 0;
    RAM_BANK = 1;
    asm ("sei");
    ae_flag = flag;
    ae_addr = addr;
    ae_lname (lname, name);
    cbm_k_setnam (lname);
    cbm_k_setlfs (2, 8, 2);        /* device 8, SA 2 = headerless */
    ae_kload ();
    st = ae_status;
    asm ("cli");
    ae_clrchn ();                  /* keyboard back as the input channel */
    VERA.irq_enable = oldien;
    return st;
}

/* Copy a run of VRAM bytes from one address to another through the data
 * port.  The address is reprogrammed for every byte, which keeps the code
 * independent of ADDRSEL/DATA1 behaviour. */
static void vram_move (unsigned long dst, unsigned long src, unsigned len)
{
    unsigned i;

    for (i = 0; i < len; ++i) {
        unsigned char b;
        vera_addr (src + i);
        b = VERA.data0;
        vera_addr (dst + i);
        VERA.data0 = b;
    }
}

unsigned char ae_load_raw_asset (const char *name, unsigned address,
                                 unsigned char high, unsigned size)
{
    dbg ('A');
    if ((high & 0x01) == 0 && address == 0) {
        /* Bank-0 assets at address 0 (ENDING/GOVER): stage, then copy. */
        ae_load (name, 2, (unsigned) AE_STAGE);
        vram_move (0, AE_STAGE, size);
        dbg ('V');
        return 1;
    }
    ae_load (name, (high & 0x01) ? 3 : 2, address);
    dbg ('V');

    return 1;
}

/* Stage a level file in VRAM so the C code can stream it with read(). */
void ae_stage_vram (const char *name)
{
    ae_load (name, 2, (unsigned) AE_STAGE);
}

unsigned char ae_read_stage (unsigned long pos)
{
    vera_addr (AE_STAGE + pos);
    return VERA.data0;
}
