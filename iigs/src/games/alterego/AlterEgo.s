; Alter Ego (NES, NROM) on the Apple IIgs

            TYP   $B3         ; S16 file
            DSK   AlterEgoGS

; No XPL: build.js compacts the load file (scripts/omf-compact.js: removes DS
; records and reserved space) and ExpressLoad cannot load those.

; Segment #1 -- Main execution block

            ASM   Main.s
            KND   #$1100
            SNA   MAIN

            ASM   Stack.s
            KND   $0012
            SNA   STKDP

; The engine (PPU simulation, renderers, blitter, tile/sprite compilers)

            ASM   ../../Engine.s
            KND   #$1100
            SNA   ENGINE

; PPU blitter

            ASM   TemplateLiteBank1.s
            KND   #$1100
            SNA   PPU1

            ASM   TemplateLiteBank2.s
            KND   #$1100
            SNA   PPU2

; Converted tile storage

            ASM   TileData.s
            KND   #$1100
            SNA   CHRDATA

; ROM: support code + the original 32KB PRG in one bank

            ASM   rom.s
            KND   #$1100
            SNA   AEROM

; PPU memory and PPU shadow storage

            ASM   PPU.s
            KND   #$1100
            SNA   PPURAM

; Palette swizzle tables are folded into MAIN (keeps the load file at 8
; segments for the GS/OS S16 loader).

