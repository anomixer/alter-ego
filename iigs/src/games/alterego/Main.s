; The runtime's declarations (the build expands the list: src/runtime/head.txt)
; mput ../../runtime/head.txt
; AUTOINC:BEGIN (do not edit -- managed by scripts/gen-includes.js)
            REL
            use   Locator.Macs
            use   Load.Macs
            use   Mem.Macs
            use   Misc.Macs
            use   Util.Macs
            use   EDS.GSOS.Macs
            use   GTE.Macs.s
            put    ../../Externals.s
            put    ../../core/Defs.s
            put    ../../rom/rom_kbd_macs.s
            put    ../../ImportEngine.s
; AUTOINC:END

            put   Config.s
            put   pal_defs.s                  ; PAL_* constants from palettes/

            mx    %00

            phk
            plb

; NROM: vertical mirroring at power on.
            tax                           ; X = memory manager user ID (passed in A by GS/OS)
            lda   #VERTICAL_MIRRORING     ; A = cartridge nametable mirroring at power on
            jsr   NES_StartUp

; The C PRG's zero page is linked at $0020, so it has to run with D=$0000.
; The runtime's default DP_NES is in the STKDP bank and would make every
; zeropage access miss.
            lda   #0
            sta   DP_NES

; Select the title palette (also installed by InitPlayfield during NES_StartUp).
            jsr   SetDefaultPalette

; Run the C game's reset code from ROMBase+$FFFC.
            jsr   NES_ColdBoot

:start
            jsr   NES_EvtLoop

            cmp   #USER_SAYS_QUIT
            beq   quit

            cmp   #USER_SAYS_RESET
            bne   quit

            jsr   NES_WarmBoot
            bra   :start

quit
            jsr   NES_ShutDown

            _QuitGS    qtRec
qtRec       adrl  $0000
            da    $00

; Names of the save and preference files (used by misc/io.s)
SAVE_FILENAME strl '1/ae.sav'
PREF_FILENAME strl '1/ae.prefs'

; Engine callbacks (macros only)
            put   Hooks.s

; ===========================================================================
; Game code
; ===========================================================================
            mx    %00

; Called by NES_StartUp before the ROM's reset code runs.  The generated
; palette code needs its swizzle tables installed before the title is drawn.
InitPlayfield
            jmp   SetDefaultPalette

            mx    %00

; CUSTOM_RENDER_SCREEN.  Gameplay uses one continuous source band: SHR 0-199
; maps to NES 16-215 through the grid's y_offset.  The title/credits keep the
; full renderer and their own vertical lift.
CustomRender ENT
            ldal  LayoutActiveAbs
            and   #$00FF
            bne   :draw

            ldal  OAM_COPY
            beq   :inactive
            lda   #1
            stal  LayoutActiveAbs
            bra   :draw

:inactive
            lda   #31
            stal  YOffsetAbs

            ; The title blinks PRESS START by toggling the horizontal
            ; nametable every 16 frames.  Because this custom renderer draws
            ; the full screen itself, it must latch that scroll before drawing.
            ldal  _ppuscroll_y
            tay
            ldal  _ppuscroll_x
            tax

            ; The title's PRESS START lives on nametable 0; the game's
            ; scroll alternates between the two nametables, but the custom
            ; renderer has to select the page itself.  Use a render counter
            ; so PRESS START really blinks.  Credits scroll with y=8, and the
            ; well-done screen scrolls x=-4; both stay on nametable 0.
            ldal  _ppuscroll_x
            and   #$00FF
            bne   :title_nt0
            ldal  _ppuscroll_y
            and   #$00FF
            bne   :title_nt0
            ldal  titleBlink
            inc
            stal  titleBlink
            and   #$0010
            beq   :title_nt0
            lda   #1
            bra   :title_scroll
:title_nt0
            lda   #0
:title_scroll
            jsl   NES_SetScroll

            lda   #0
            ldx   #200
            jsl   PPU_DrawScreenRange
            lda   #0
            stal  YOffsetAbs
            lda   #0
            sec
            rtl

:draw
            ; The grid renderer draws the playfield from its dirty cells.  Keep
            ; the same source offset for the fallback full renderer.
            lda   #16
            stal  YOffsetAbs
            lda   #0
            clc
            rtl
            mx    %00

titleBlink    dw    0

; Palette management generated from palettes/
            put   pal_transitions.s
            put   palettes.s                ; swizzle tables (was the PALDATA segment)

; Runtime code (the build expands the list: src/runtime/code.txt)
            mput  ../../runtime/code.txt
; AUTOINC:BEGIN (do not edit -- managed by scripts/gen-includes.js)
            put    ../../misc/App.Msg.s
            put    ../../misc/io.s
            put    ../../apu/apu.s
            put    ../../rom/scaffold.s
            put    ../../rom/rom_color.s
            put    ../../rom/rom_helpers.s
            put    ../../rom/rom_input.s
            put    ../../rom/rom_kbd_basic.s
            put    ../../rom/rom_exec.s
            put    ../../rom/rom_config.s
            put    ../../rom/rom_config_setup.s
            put    ../../core/ControlBits.s
            put    ../../core/CoreImpl.s
            put    ../../core/Graphics.s
            put    ../../core/Math.s
            put    ../../core/Memory.s
; AUTOINC:END
