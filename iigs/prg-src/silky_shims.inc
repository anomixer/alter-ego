; Fixed shim table at $7E00 in the ROMBase bank.  Each entry is a 3-byte JMP
; into rom_inject.s; the C runtime calls the entries with JSR, so the shim's
; RTS returns to the C code.
;
; The table is declared here and generated in rom.s.  Keep the addresses in
; sync with the order of SEGMENT_JUMP_TABLE in rom.s.
SHIM_2000      = $7E00   ; STA $2000 - PPUCTRL
SHIM_2001      = $7E03   ; STA $2001 - PPUMASK
SHIM_2002      = $7E06   ; LDA $2002 - PPUSTATUS
SHIM_2003      = $7E09   ; STA $2003 - OAMADDR
SHIM_2005      = $7E0C   ; STA $2005 - PPUSCROLL
SHIM_2006      = $7E0F   ; STA $2006 - PPUADDR
SHIM_2007      = $7E12   ; STA $2007 - PPUDATA
SHIM_2007_LDA  = $7E15   ; LDA $2007 - PPUDATA (read)
SHIM_4014      = $7E18   ; STA $4014 - OAMDMA
SHIM_2006_X    = $7E1B   ; STX $2006 - PPUADDR (high byte)
SHIM_YIELD     = $7E1E   ; JSYIELD - long-call the silky yield, then RTS
SHIM_NOP       = $7E21   ; unused / reserved
SHIM_NOP2      = $7E21   ; unused / reserved
SHIM_NOP3      = $7E24   ; unused / reserved
SHIM_NOP4      = $7E27   ; unused / reserved
SHIM_NOP5      = $7E2A   ; unused / reserved
SHIM_NOP6      = $7E2D   ; unused / reserved
SHIM_NOP7      = $7E30   ; unused / reserved
SHIM_NOP8      = $7E33   ; unused / reserved
