; Bank of memory that holds the NES PPU RAM from $0000 - $3FFF and shadow data.
PPU_MEM     ENT
CHR_ROM     ENT
            putbin chr.bin          ; 8K of CHR-ROM at PPU memory $0000 - $2000
PPU_CIRAM   ENT
            ds    $800            ; CIRAM buffer
            ds    $1700           ; padding
PALETTE_RAM ds    $100            ; $3F00 - $3F14 palette RAM
