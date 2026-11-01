; Alter Ego -- engine callbacks (title-screen PoC)
;
; The generated palette management is used: ApplyPaletteChange identifies the
; NES palette after the C game uploads it, and PRE_RENDER applies it.

            mx    %00

PRE_EVT_LOOP mac
;
             <<<

POST_EVT_LOOP mac
;
             <<<

EVT_LOOP_BEGIN mac
;
             <<<

EVT_LOOP_END mac
;
             <<<

PRE_RENDER   mac
             jsl  ApplyPaletteChange
             <<<

POST_RENDER  mac
;
             <<<

SPRITE_PRE_DRAW  mac
;
             <<<

SPRITE_CLIP equ 0

CONFIG_APPLY_HOOK mac
;
             <<<

; The engine's generated palette handlers are used; no game-specific table.
CUSTOM_PPU_PALETTE_DISPATCH equ 0

CUSTOM_PPU_CTRL_LOCK equ 0
CUSTOM_PPU_SCROLL_LOCK equ 0

CustomRender EXT
CUSTOM_RENDER_SCREEN equ 1
CUSTOM_RENDER_SCREEN_ADDR equ CustomRender

CONFIG_GAME_DEFAULTS mac
;
             <<<
