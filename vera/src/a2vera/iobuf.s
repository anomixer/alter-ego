; Fixed, page-aligned ProDOS buffers. BASIC.SYSTEM protects high RAM in the
; ProDOS memory bitmap; malloc buffers there fail OPEN with error $56.
; Main and music buffers use independent fixed pages selected by the build.
.setcpu "6502"
.include "errno.inc"
.import popax
.importzp ptr1
.export iobuf_alloc, iobuf_free

.segment "BSS"
used: .res 1

.segment "CODE"
iobuf_alloc:
        jsr popax              ; discard alignment (caller requests $0100)
        jsr popax              ; pointer to fdtab buffer field
        sta ptr1
        stx ptr1+1
        lda used
        and #1
        beq first
.if IOBUF_COUNT = 2
        lda used
        and #2
        bne full
        lda #2
        ldx #>(IOBUF_BASE+$0400)
        bne store
.endif
full:   lda #ENOMEM
        ldx #0
        rts
first:  lda #1
        ldx #>IOBUF_BASE
store:  ora used
        sta used
        lda #0
        ldy #0
        sta (ptr1),y
        iny
        txa
        sta (ptr1),y
        lda #0
        tax
        rts

iobuf_free:
.if IOBUF_COUNT = 2
        cpx #>(IOBUF_BASE+$0400)
        bne release_first
        lda used
        and #$FD
        sta used
        rts
.endif
release_first:
        lda used
        and #$FE
        sta used
        rts
