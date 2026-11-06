; KERNAL LOAD called exactly the way loader.s does it; no fastcall tricks.
.setcpu "65C02"
.import _ae_flag, _ae_addr, _ae_end, _ae_err, _ae_status
.export _ae_kload
.segment "CODE"
_ae_kload:
        lda _ae_flag
        ldx _ae_addr
        ldy _ae_addr+1
        jsr $FFD5
        stx _ae_end
        sty _ae_end+1
        sta _ae_err
        php
        pla
        sta _ae_status
        rts
