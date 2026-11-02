; Compact music data generated from the original FamiTone-compatible modules.
; These are data-only exports for the new VERA player; no Mockingboard code is
; linked here.
.setcpu "6502"

.segment "FTMDATA"
.export _fami_module_directory
_fami_module_directory:
	.word music_title_module,music_level1_module,music_level2_module
	.word music_level2_module,music_level3_module,music_level4_module
	.word music_level5_module,music_gameover_module,music_done_module
	.word music_level2_module

.include "music_instruments.s"
.include "music_title.s"
.include "music_level1.s"
.include "music_level2.s"
.include "music_level3.s"
.include "music_level4.s"
.include "music_level5.s"
.include "music_gameover.s"
.include "music_done.s"
