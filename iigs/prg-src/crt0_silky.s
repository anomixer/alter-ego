; Startup code for the silky-gs Alter Ego title-screen PoC.
; Derived from the cc65 NES crt0, with the NES hardware setup removed:
;   - no sei/txs (the runtime owns the NES task stack and interrupt state)
;   - no PPU status polling
;   - no RAM/VRAM clear (the runtime owns those)
;   - NMI returns with rtl, because silky invokes it with jsl
;   - PPU accesses go through the fixed shim table at $7E00

        .export _exit
        .export __STARTUP__:absolute=1
        .import initlib
        .import push0,_main,zerobss,copydata
        .import popa
        .import _oam_clear
        .import FamiToneInit,FamiToneSfxInit,FamiToneUpdate
        .import sounds

; Linker generated symbols
        .import __RAM_START__   ,__RAM_SIZE__
        .import __STARTUP_LOAD__,__STARTUP_RUN__,__STARTUP_SIZE__
        .import __CODE_LOAD__   ,__CODE_RUN__   ,__CODE_SIZE__
        .import __RODATA_LOAD__ ,__RODATA_RUN__ ,__RODATA_SIZE__

        .include "zeropage.inc"
        .include "memmap.inc"
        .include "silky_shims.inc"

.segment        "STARTUP"

start:
_exit:

        ; The C runtime's software stack: the byte just past the BSS/RAM area.
        ; It grows down through $0700.., below the ROM support code at $0800.
        jsr     _oam_clear
        jsr     zerobss
        jsr     copydata

        lda     #<(__RAM_START__+__RAM_SIZE__)
        sta     sp
        lda     #>(__RAM_START__+__RAM_SIZE__)
        sta     sp+1

        jsr     initlib

        ; Bring up FamiTone2 and the SFX table before the C game starts.
        ; FamiTone is 8-bit code; entering it with 16-bit A/X would turn its
        ; one-byte APU stores into two-byte stores that overwrite the
        ; following instructions.
        sep     #$20
        lda     #1
        jsr     FamiToneInit
        ldx     #<sounds
        ldy     #>sounds
        jsr     FamiToneSfxInit

        ; Enable NMI and let the runtime's PPU shim record it.
        lda     #%10000000
        sta     <PPU_CTRL_VAR
        jsr     SHIM_2000

        lda     #1
        sta     <RAND_SEED

        jmp     _main


nmi:
        pha
        txa
        pha
        tya
        pha

        lda     <VRAMUPDATE
        bne     @upd
        jmp     @skipUpd

@upd:
        lda     #$00
        jsr     SHIM_2003
        lda     #>OAM_BUF
        jsr     SHIM_4014

        lda     #$3f
        jsr     SHIM_2006
        lda     #$00
        jsr     SHIM_2006

        lda     PAL_BUF+0
        jsr     SHIM_2007
        lda     PAL_BUF+1
        jsr     SHIM_2007
        lda     PAL_BUF+2
        jsr     SHIM_2007
        lda     PAL_BUF+3
        jsr     SHIM_2007

        jsr     SHIM_2007_LDA
        lda     PAL_BUF+5
        jsr     SHIM_2007
        lda     PAL_BUF+6
        jsr     SHIM_2007
        lda     PAL_BUF+7
        jsr     SHIM_2007

        jsr     SHIM_2007_LDA
        lda     PAL_BUF+9
        jsr     SHIM_2007
        lda     PAL_BUF+10
        jsr     SHIM_2007
        lda     PAL_BUF+11
        jsr     SHIM_2007

        jsr     SHIM_2007_LDA
        lda     PAL_BUF+13
        jsr     SHIM_2007
        lda     PAL_BUF+14
        jsr     SHIM_2007
        lda     PAL_BUF+15
        jsr     SHIM_2007

        jsr     SHIM_2007_LDA
        lda     PAL_BUF+17
        jsr     SHIM_2007
        lda     PAL_BUF+18
        jsr     SHIM_2007
        lda     PAL_BUF+19
        jsr     SHIM_2007

        jsr     SHIM_2007_LDA
        lda     PAL_BUF+21
        jsr     SHIM_2007
        lda     PAL_BUF+22
        jsr     SHIM_2007
        lda     PAL_BUF+23
        jsr     SHIM_2007

        jsr     SHIM_2007_LDA
        lda     PAL_BUF+25
        jsr     SHIM_2007
        lda     PAL_BUF+26
        jsr     SHIM_2007
        lda     PAL_BUF+27
        jsr     SHIM_2007

        jsr     SHIM_2007_LDA
        lda     PAL_BUF+29
        jsr     SHIM_2007
        lda     PAL_BUF+30
        jsr     SHIM_2007
        lda     PAL_BUF+31
        jsr     SHIM_2007

        ldx     <NAME_UPD_LEN
        beq     @skipUpd
        ldy     #0
@updName:
        lda     (NAME_UPD_ADR),y
        iny
        jsr     SHIM_2006
        lda     (NAME_UPD_ADR),y
        iny
        jsr     SHIM_2006
        lda     (NAME_UPD_ADR),y
        iny
        jsr     SHIM_2007
        dex
        bne     @updName

@skipUpd:
        lda     #0
        jsr     SHIM_2006
        jsr     SHIM_2006

        lda     <SCROLL_X
        jsr     SHIM_2005
        lda     <SCROLL_Y
        jsr     SHIM_2005
        lda     <PPU_CTRL_VAR
        jsr     SHIM_2000

        inc     <FRAMECNT1
        inc     <FRAMECNT2
        lda     <FRAMECNT2
        cmp     #6
        bne     @skipNtsc
        lda     #0
        sta     <FRAMECNT2
@skipNtsc:

        ; Advance FamiTone2 once per NES frame.
        jsr     FamiToneUpdate

        pla
        tay
        pla
        tax
        pla
        rtl

irq:
        rti


.segment "VECTORS"

        .word nmi       ; $fffa vblank nmi
        .word start     ; $fffc reset
        .word irq       ; $fffe irq / brk
