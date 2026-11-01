; Alter Ego -- the ROM bank
;
; $0000-$07FF  NES RAM (the C game's zero page, stack, OAM/palette buffers)
; $0800-$09FF  y_exclude / tile_exclude tables (read by InitYExclude)
; $0A00-...    injected PPU/APU hooks and the yield trampoline
; $7E00-$7E2F  fixed 3-byte JSR target table, used by the patched C runtime
; $8000-$FFFF  original 32KB NES PRG, vectors included
;
; The PRG is exactly 32768 bytes and the whole segment is 65536 bytes, so it
; occupies one ROMBase bank.

            mx    %11

HORIZONTAL_MIRRORING equ $01
VERTICAL_MIRRORING   equ $02

ROMBase     ENT
            ds    $0800-*              ; NES RAM ($0000-$07FF)

y_exclude   ENT
            ds    256

tile_exclude ENT
            ds    256

            put   ../../rom/rom_inject.s

; Called from the fixed table below when the C runtime's _ppu_waitnmi runs.
; yield returns here after the GS task has run the next NES frame.
SHIM_YIELD_IMPL
; _ppu_waitnmi must wait for the next VBL even before the game enables NMI
; (the credits screen waits while PPUCTRL bit 7 is still clear).
            jsl   yieldFrame
            rts

            ds    $7E00-*              ; fixed shim dispatch table

            jmp   STA_2000
            jmp   STA_2001
            jmp   LDA_2002
            jmp   STA_2003
            jmp   STA_2005
            jmp   STA_2006
            jmp   STA_2007
            jmp   LDA_2007
            jmp   STA_4014
            jmp   STX_2006
            jmp   SHIM_YIELD_IMPL
            jmp   SHIM_YIELD_IMPL
            jmp   SHIM_YIELD_IMPL
            jmp   SHIM_YIELD_IMPL
            jmp   SHIM_YIELD_IMPL

            ; $7E30-$7E5C  APU write trampolines used by FamiTone2
            ds    3                    ; align with SHIM_APU_* at $7E30
            jmp   STA_4000
            jmp   STA_4001
            jmp   STA_4002
            jmp   STA_4003
            jmp   STA_4004
            jmp   STA_4005
            jmp   STA_4006
            jmp   STA_4007
            jmp   STA_4008
            jmp   STA_400a
            jmp   STA_400b
            jmp   STA_400c
            jmp   STA_400e
            jmp   STA_400f
            jmp   STA_4015

            ds    $8000-*              ; 32KB NES PRG at its NES address

            putbin prg.bin
