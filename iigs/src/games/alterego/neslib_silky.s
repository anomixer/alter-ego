	.include "memmap.inc"
	.include "silky_shims.inc"

	.export _pal_all,_pal_bg,_pal_spr,_pal_col,_pal_clear,_pal_fade
	.export _pal_fade_to_all,_pal_fade_to_bg,_pal_fade_to_spr
	.export _ppu_off,_ppu_on_all,_ppu_on_bg,_ppu_on_spr
	.export _oam_clear,_oam_spr,_oam_meta_spr
	.export _ppu_waitnmi
	.export _unrle_vram
	.export _scroll
	.export _bank_spr,_bank_bg
	.export _vram_read
	.export _music_play,_music_stop,_music_pause
	.export _sfx_play
	.export _pad_poll,_pad_trigger
	.export _pad_space
	.export _rand,_setrand
	.export _set_vram_update,_vram_adr,_vram_put,_vram_fill,_vram_inc
	.export _memcpy
	.import popa,popax
	.import FamiToneMusicStart,FamiToneMusicStop,FamiToneMusicPause,FamiToneSfxStart



;void __fastcall__ pal_all(const char *data);

_pal_all:
	sta <PTR
	stx <PTR+1
	ldy #$00
	ldx #$00
	lda #$20

pal_copy:
	sta <LEN
@0:
	lda (PTR),y
	sta PAL_BUF,x
	inx
	iny
	dec <LEN
	bne @0
	rts



;void __fastcall__ pal_bg(const char *data);

_pal_bg:
	sta <PTR
	stx <PTR+1
	ldy #$00
	ldx #$00
	lda #$10
	jmp pal_copy



;void __fastcall__ pal_spr(const char *data);

_pal_spr:
	sta <PTR
	stx <PTR+1
	ldy #$00
	ldx #$10
	txa
	jmp pal_copy



;void __fastcall__ pal_col(unsigned char index,unsigned char color);

_pal_col:
	sta <PTR
	jsr popa
	and #$1f
	tax
	lda <PTR
	sta PAL_BUF,x
	rts



;void __fastcall__ pal_clear(void);

_pal_clear:
	lda #$0f
	ldx #0
@1:
	sta PAL_BUF,x
	inx
	cpx #$20
	bne @1
	rts



;void __fastcall__ pal_fade(void);

_pal_fade:
	ldx #0
@1:
	lda PAL_BUF,x
	cmp #$10
	bcs @2
	lda #$0f
	bne @3
@2:
	sec
	sbc #$10
@3:
	sta PAL_BUF,x
	inx
	cpx #$20
	bne @1
	rts



;void __fastcall__ pal_fade_to_all(const unsigned char *pal);

_pal_fade_to_all:
	sta <PTR
	stx <PTR+1
	ldx #0
	ldy #0
	lda #32

pal_fade_to:
	sta <LEN
@1:
	lda PAL_BUF,x
	cmp (PTR),y
	beq @4
	cmp #$0f
	bne @2
	lda (PTR),y
	and #$0f
	jmp @3
@2:
	clc
	adc #$10
@3:
	sta PAL_BUF,x
@4:
	iny
	inx
	dec <LEN
	bne @1

	rts



;void __fastcall__ pal_fade_to_bg(const unsigned char *pal);

_pal_fade_to_bg:
	sta <PTR
	stx <PTR+1
	ldx #0
	ldy #0
	lda #16
	jmp pal_fade_to



;void __fastcall__ pal_fade_to_spr(const unsigned char *pal);

_pal_fade_to_spr:
	sta <PTR
	stx <PTR+1
	ldx #16
	ldy #0
	lda #16
	jmp pal_fade_to



;void __fastcall__ ppu_off(void);

_ppu_off:
	lda #0
	jsr SHIM_2001
	jsr SHIM_2000
	rts



;void __fastcall__ ppu_on_all(void);

_ppu_on_all:
	lda #%00011110
	jsr SHIM_2001
	lda <PPU_CTRL_VAR
	jsr SHIM_2000
	rts



;void __fastcall__ ppu_on_bg(void);

_ppu_on_bg:
	lda #%00001110
	jsr SHIM_2001
	lda <PPU_CTRL_VAR
	jsr SHIM_2000
	rts



;void __fastcall__ ppu_on_spr(void);

_ppu_on_spr:
	lda #%00011110
	jsr SHIM_2001
	lda <PPU_CTRL_VAR
	jsr SHIM_2000
	rts



;void __fastcall__ oam_clear(void);

_oam_clear:
	ldx #0
	lda #$ff
@1:
	sta OAM_BUF,x
	inx
	inx
	inx
	inx
	bne @1
	rts



;unsigned char __fastcall__ oam_spr(unsigned char x,unsigned char y,unsigned char chrnum,unsigned char attr,unsigned char sprid);

_oam_spr:
	phk
	plb
	sta <NEXTSPR
	asl a
	asl a
	tax

	jsr popa
	sta OAM_BUF+2,x
	jsr popa
	sta OAM_BUF+1,x
	jsr popa
	sta OAM_BUF+0,x
	jsr popa
	sta OAM_BUF+3,x

	inc <NEXTSPR
	lda <NEXTSPR
	and #$3f
	rts



;unsigned char __fastcall__ oam_meta_spr(unsigned char x,unsigned char y,unsigned char sprid,const unsigned char *data);

_oam_meta_spr:
	sta <PTR
	stx <PTR+1

	jsr popa
	asl a
	asl a
	tax

	jsr popa
	sta <SCRY
	jsr popa
	sta <SCRX

	ldy #0
@1:
	lda (PTR),y		;x offset
	cmp #$80
	beq @2
	iny
	clc
	adc <SCRX
	sta OAM_BUF+3,x
	lda (PTR),y		;y offset
	iny
	clc
	adc <SCRY
	sta OAM_BUF+0,x
	lda (PTR),y		;tile
	iny
	sta OAM_BUF+1,x
	lda (PTR),y		;attribute
	iny
	sta OAM_BUF+2,x
	inx
	inx
	inx
	inx
	jmp @1

@2:
	txa
	lsr a
	lsr a
	rts



;void __fastcall__ ppu_waitnmi(void);

_ppu_waitnmi:
	; The silky runtime owns the frame clock.  SHIM_YIELD is a table entry in
	; the ROMBase bank that long-calls yield, then returns here.  Mark the
	; palette (and OAM) dirty so the ROM's NMI handler uploads PAL_BUF.
	lda #1
	sta <VRAMUPDATE
	jsr SHIM_YIELD
	rts



;void __fastcall__ unrle_vram(const unsigned char *data,unsigned int vram);

_unrle_vram:
	pha
	jsr SHIM_2006_X
	pla
	jsr SHIM_2006

	jsr popax
	sta <RLE_LOW
	stx <RLE_HIGH

	ldy #0
	jsr rle_byte
	sta <RLE_TAG
@1:
	jsr rle_byte
	cmp <RLE_TAG
	beq @2
	jsr SHIM_2007
	sta <RLE_BYTE
	jmp @1
@2:
	jsr rle_byte
	cmp #0
	beq @4
	tax
	lda <RLE_BYTE
@3:
	jsr SHIM_2007
	dex
	bne @3
	beq @1
@4:
	rts

rle_byte:
	lda (RLE_LOW),y
	inc <RLE_LOW
	bne @1
	inc <RLE_HIGH
@1:
	rts



;void __fastcall__ scroll(unsigned int x,unsigned int y);

_scroll:
	sta <SCROLL_Y
	txa
	asl a
	and #$02
	sta <TEMP

	jsr popax
	sta <SCROLL_X
	txa
	and #$01
	ora <TEMP
	sta <TEMP
	lda <PPU_CTRL_VAR
	and #$fc
	ora <TEMP
	sta <PPU_CTRL_VAR
	rts



;void __fastcall__ bank_spr(unsigned char n);

_bank_spr:
	and #$01
	asl a
	asl a
	asl a
	sta <TEMP
	lda <PPU_CTRL_VAR
	and #%11110111
	ora <TEMP
	sta <PPU_CTRL_VAR
	rts



;void __fastcall__ bank_bg(unsigned char n);

_bank_bg:
	and #$01
	asl a
	asl a
	asl a
	asl a
	sta <TEMP
	lda <PPU_CTRL_VAR
	and #%11101111
	ora <TEMP
	sta <PPU_CTRL_VAR
	rts



;void __fastcall__ vram_read(unsigned char *dst,unsigned int adr,unsigned int size);

_vram_read:
	sta <TEMP
	stx <TEMP+1

	jsr popax
	jsr SHIM_2006_X
	jsr SHIM_2006
	jsr SHIM_2007_LDA

	jsr popax
	sta <TEMP+2
	stx <TEMP+3

	ldy #0
@1:
	jsr SHIM_2007_LDA
	sta (TEMP+2),y
	inc <TEMP+2
	bne @2
	inc <TEMP+3
@2:
	lda <TEMP
	bne @3
	dec <TEMP+1
@3:
	dec <TEMP
	lda <TEMP
	ora <TEMP+1
	bne @1

	rts



;void __fastcall__ music_play(const unsigned char *data);

_music_play:
	stx <PTR
	tax
	ldy <PTR
	jmp FamiToneMusicStart



;void __fastcall__ music_stop(void);

_music_stop:
	jmp FamiToneMusicStop



;void __fastcall__ music_pause(unsigned char pause);

_music_pause:
	jmp FamiToneMusicPause



;void __fastcall__ sfx_play(unsigned char sound,unsigned char channel);

_sfx_play:
	and #$03
	tax
	lda @sfxPriority,x
	tax
	jsr popa
	jmp FamiToneSfxStart

@sfxPriority:
	.byte 0,15,30,45



;unsigned char __fastcall__ pad_poll(void);

_pad_poll:
	; Read the IIgs keyboard directly.  $E0C010 bit 7 says whether any
	; key is down; reading it also clears the keyboard strobe.  $E0C000
	; then holds the key code in bits 0-6.
	;
	; Mapping (NES pad bits: A=01 B=02 SELECT=04 START=08
	; UP=10 DOWN=20 LEFT=40 RIGHT=80):
	;   arrows        directions
	;   Return        START
	;   Tab           SELECT
	;   Z / Space     A
	;   X             B
	php
	sep	#$20
	lda	#$00
	sta	_pad_space	; set only by the Space key (see below)
	lda	$E0C010
	and	#$80
	bne	@k0
	jmp	@no_key		; out of branch range
@k0:	lda	$E0C000
	and	#$7F

	cmp	#$08		; left arrow
	bne	@k1
	lda	#$40
	bra	@store
@k1:	cmp	#$15		; right arrow
	bne	@k2
	lda	#$80
	bra	@store
@k2:	cmp	#$0B		; up arrow
	bne	@k3
	lda	#$10
	bra	@store
@k3:	cmp	#$0A		; down arrow
	bne	@k4
	lda	#$20
	bra	@store
@k4:	cmp	#$0D		; Return (press start / pause)
	beq	@start
	cmp	#$24		; Return (ADB code)
	beq	@start
	cmp	#$03		; keypad Enter
	beq	@start
	cmp	#$50		; P (also start; diagnostic-friendly)
	beq	@start
	cmp	#$70		; p
	bne	@k5
@start:	lda	#$08
	bra	@store
@k5:	cmp	#$09		; Tab
	bne	@k6
	lda	#$04
	bra	@store
@k6:	cmp	#$5A		; Z
	beq	@a
	cmp	#$7A		; z
	beq	@a
	cmp	#$1A		; Ctrl-Z / some ADB keyboards
	beq	@a
	cmp	#$06		; raw ADB Z
	beq	@a
	cmp	#$20		; Space
	bne	@k7
	lda	#$01
	sta	_pad_space	; Space is A, but the game can tell it apart
	bra	@a
@k7:	cmp	#$58		; X
	beq	@b
	cmp	#$78		; x
	beq	@b
	cmp	#$18		; Ctrl-X / some ADB keyboards
	beq	@b
	cmp	#$07		; raw ADB X
	beq	@b
	; Last resort: compare the low five bits only.  Keyboards, ROMs and
	; emulators differ in the upper bits of $C000 (case bit 5, the strobe
	; bit 7, some set bit 6), and a Caps Lock-off key must still work:
	; "x"/"X" is always $18 in the low five bits, "z"/"Z" is $1A.
	and	#$1F
	cmp	#$1A		; Z
	beq	@a
	cmp	#$18		; X
	bne	@no_key
@b:	lda	#$02
	bra	@store
@a:	lda	#$01
	bra	@store

@no_key:
	lda	#$00
@store:
	sta	<PAD_STATE
	; trigger = newly pressed bits = now & ~previous
	eor	<PAD_STATEP
	and	<PAD_STATE
	sta	<PAD_STATET
	lda	<PAD_STATE
	sta	<PAD_STATEP
	plp
	rts

@padPollPort:
	ldy #$01
	sty CTRL_PORT1
	dey
	sty CTRL_PORT1
	ldy #8
@1:
	lda CTRL_PORT1
	and #$01
	clc
	beq @2
	sec
@2:
	ror <PAD_BUF,x
	dey
	bne @1

	inx
	rts



;unsigned char __fastcall__ pad_trigger(void);

_pad_trigger:
	jsr _pad_poll
	lda <PAD_STATET
	rts



;unsigned char __fastcall__ rand(void);
;Galois random generator, found somewhere
;out: A random number 0..255

_rand:
	lda <RAND_SEED
	asl a
	bcc @1
	eor #$cf
@1:
	sta <RAND_SEED
	rts



;void __fastcall__ setrand(unsigned char seed);

_setrand:
	sta <RAND_SEED
	rts



;void __fastcall__ set_vram_update(unsigned char len,unsigned char *buf);

_set_vram_update:
	sta <NAME_UPD_ADR
	stx <NAME_UPD_ADR+1
	jsr popa
	sta <NAME_UPD_LEN
	rts



;void __fastcall__ vram_adr(unsigned int adr);

_vram_adr:
	jsr SHIM_2006_X
	jsr SHIM_2006
	rts



;void __fastcall__ vram_put(unsigned char n);

_vram_put:
	jsr SHIM_2007
	rts



;void __fastcall__ vram_fill(unsigned char n,unsigned char len);

_vram_fill:
	tax
	jsr popa
@1:
	jsr SHIM_2007
	dex
	bne @1
	rts



;void __fastcall__ vram_inc(unsigned char n);

_vram_inc:
	beq @1
	lda #$04
@1:
	sta <TEMP
	lda <PPU_CTRL_VAR
	and #$fb
	ora <TEMP
	sta <PPU_CTRL_VAR
	jsr SHIM_2000
	rts



;void __fastcall__ memcpy(void *dst,void *src,unsigned int len);

_memcpy:
	sta <LEN
	stx <LEN+1
	jsr popax
	sta <SRC
	stx <SRC+1
	jsr popax
	sta <DST
	stx <DST+1

	ldx #0
@1:
	lda <LEN+1
	beq @2
	jsr @3
	dec <LEN+1
	inc <SRC+1
	inc <DST+1
	jmp @1
@2:
	ldx <LEN
	beq @5

@3:
	ldy #0
@4:
	lda (SRC),y
	sta (DST),y
	iny
	dex
	bne @4
@5:
	rts
; Set to 1 by _pad_poll only while the Space key is the key being read.
; The game uses it to let Space audition the sound-test selection while Z
; keeps its own "stop the music" role.
	.segment "BSS"
_pad_space:	.res	1