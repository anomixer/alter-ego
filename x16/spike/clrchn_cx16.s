; CLRCHN wrapper (the CBM header in this cc65 build does not declare one).
.setcpu "65C02"
.export _ae_clrchn
.segment "CODE"
_ae_clrchn:
        jsr $FFCC
        rts
