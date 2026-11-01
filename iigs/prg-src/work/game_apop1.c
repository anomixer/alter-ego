#include "neslib.h"

#include "credits.h"
#include "title.h"
#include "map0.h"
#include "map1.h"
#include "map2.h"
#include "map3.h"
#include "map4.h"
#include "map5.h"
#include "map6.h"
#include "map7.h"
#include "map8.h"
#include "map9.h"
#include "map10.h"
#include "map11.h"
#include "map12.h"
#include "map13.h"
#include "map14.h"
#include "map15.h"
#include "map16.h"
#include "map17.h"
#include "map18.h"
#include "map19.h"
#include "map20.h"
#include "map21.h"
#include "map22.h"
#include "map23.h"
#include "map24.h"
#include "map25.h"
#include "gameover.h"
#include "welldone.h"
#include "palettes.h"



#define TILE_SIZE			8
#define TILE_BIT			3

#define MAP_WDT				32
#define MAP_WDT_BIT			5
#define MAP_WDT_MASK		((1<<MAP_WDT_BIT)-1)
#define MAP_HGT				20

#define DIR_NONE			0
#define DIR_LEFT			1
#define DIR_RIGHT			2
#define DIR_UP				3
#define DIR_DOWN			4

#define DONE_NOTYET			0
#define DONE_CLEAR			1
#define DONE_NOLUCK			2
#define DONE_RESTART		3
#define DONE_EXIT			4

#define PLAYER_IDLE_MAX		50
#define PLAYER_START_DELAY	50
#define PLAYER_CLEAR_DELAY	24

#define PLAYER_SPR_IDLE 	0x90
#define PLAYER_SPR_WALK		0x91
#define PLAYER_SPR_LADDER 	0x95
#define PLAYER_SPR_FALL 	0x96
#define PLAYER_SPR_ALTER 	0x97

#define TILE_EMPTY			0x00
#define TILE_WALL			0x01
#define TILE_LADDER			0x02
#define TILE_ITEM1			0x04
#define TILE_ITEM2			0x08
#define TILE_BRIDGE			0x10
#define TILE_WATER			0x20

#define TILE_FLOOR			(TILE_WALL|TILE_LADDER|TILE_BRIDGE)

#define TILE_NUM_PLAYER		0x20
#define TILE_NUM_ENEMY_R	0x21
#define TILE_NUM_ENEMY_L	0x22
#define TILE_NUM_ENEMY_U	0x23
#define TILE_NUM_ENEMY_D	0x24
#define TILE_NUM_ITEM_1		0x17
#define TILE_NUM_ITEM_2		0x18

#define ENEMY_MAX			8
#define ITEM_MAX			20
#define PART_MAX			4

#define OAM_ENEMY			0
#define OAM_PAUSE			(ENEMY_MAX<<1)
#define OAM_PARTS			(52-PART_MAX)
#define OAM_STATS			52
#define OAM_PLAYER			60

#define SFX_START			0
#define SFX_MENU			1
#define SFX_EXCHANGE		2
#define SFX_ITEM1			3
#define SFX_ITEM2			4
#define SFX_HIT				5
#define SFX_FALLING			6
#define SFX_DROP			7
#define SFX_NO_EXCHANGE		8
#define SFX_OUT_OF_EXCHANGES 9
#define SFX_BRIDGE			10
#define SFX_WALK1			11
#define SFX_WALK2			12
#define SFX_LADDER			13
#define SFX_LEVEL_CLEAR		14
#define SFX_ALL				15

#define MUS_TITLE			0
#define MUS_GAME1			1
#define MUS_GAME2			2
#define MUS_GAME3			3
#define MUS_GAME4			4
#define MUS_GAME5			5
#define MUS_GAMEOVER		6
#define MUS_WELLDONE		7
#define MUS_ALL				8

const char versionStr[]="Alter Ego v1.023a 21.02.17";

//music pointers list

/* Set by _pad_poll (neslib_silky.s): 1 while the key being read is Space.
 * Space carries the same NES A bit as Z, but the sound test uses it to
 * audition the selected SFX/BGM, so playing does not depend on X/Z. */
extern unsigned char pad_space;

extern const unsigned char music_title_data[];
extern const unsigned char music_level1_data[];
extern const unsigned char music_level2_data[];
extern const unsigned char music_level3_data[];
extern const unsigned char music_level4_data[];
extern const unsigned char music_level5_data[];
extern const unsigned char music_gameover_data[];
extern const unsigned char music_done_data[];

const unsigned char *musicData[MUS_ALL]={
music_title_data,
music_level1_data,
music_level2_data,
music_level3_data,
music_level4_data,
music_level5_data,
music_gameover_data,
music_done_data
};

//tile type flags

const unsigned char tileType[64]={
TILE_EMPTY ,TILE_WALL  ,TILE_WALL ,TILE_WALL,
TILE_WALL  ,TILE_WALL  ,TILE_WALL ,TILE_WALL,
TILE_WALL  ,TILE_WALL  ,TILE_WALL ,TILE_WALL,
TILE_WALL  ,TILE_WALL  ,TILE_WALL ,TILE_WALL,

TILE_WALL  ,TILE_WALL  ,TILE_EMPTY,TILE_EMPTY,
TILE_LADDER,TILE_EMPTY ,TILE_EMPTY,TILE_ITEM1,
TILE_ITEM2 ,TILE_WALL  ,TILE_WALL ,TILE_BRIDGE,
TILE_WATER ,TILE_WATER ,TILE_WATER,TILE_WATER,

TILE_EMPTY ,TILE_EMPTY ,TILE_EMPTY,TILE_EMPTY,
TILE_EMPTY ,TILE_WALL  ,TILE_WALL ,TILE_WALL,
TILE_WALL  ,TILE_LADDER,TILE_EMPTY,TILE_EMPTY,
TILE_WALL  ,TILE_WALL  ,TILE_WALL ,TILE_LADDER,

TILE_WALL  ,TILE_WALL  ,TILE_WALL ,TILE_WALL,
TILE_WALL  ,TILE_LADDER,TILE_EMPTY,TILE_EMPTY,
TILE_WALL  ,TILE_WALL  ,TILE_WALL ,TILE_WALL,
TILE_LADDER,TILE_WALL  ,TILE_WALL ,TILE_WALL
};

const unsigned char* level_ptrs[26*2]={
map0,palGameBG1,
map1,palGameBG1,
map2,palGameBG1,
map3,palGameBG1,
map4,palGameBG1,
map5,palGameBG1,
map6,palGameBG2,
map7,palGameBG2,
map8,palGameBG2,
map9,palGameBG2,
map10,palGameBG2,
map11,palGameBG3,
map12,palGameBG3,
map13,palGameBG3,
map14,palGameBG3,
map15,palGameBG3,
map16,palGameBG4,
map17,palGameBG4,
map18,palGameBG4,
map19,palGameBG4,
map20,palGameBG4,
map21,palGameBG5,
map22,palGameBG5,
map23,palGameBG5,
map24,palGameBG5,
map25,palGameBG5
};

//restarts, sync type

const unsigned char level_params[26*2]={
2,0,//0
2,0,//1
2,0,//2
0,0,//3
3,0,//4
4,1,//5
2,0,//6
2,0,//7
8,1,//8
2,0,//9
4,0,//10
1,0,//11
3,0,//12
2,0,//13
3,0,//14
5,1,//15
2,0,//16
9,0,//17
4,0,//18
3,1,//19
6,0,//20
2,0,//21
3,0,//22
5,0,//23
6,1,//24
0,0 //25
};

const unsigned char code_str[6]={PAD_B,PAD_LEFT,PAD_A,PAD_B,PAD_LEFT,PAD_A};

//stats and pause meta sprites

const unsigned char sprStats[]={
0 ,0,0x9b,0,//active ego
0 ,8,0xab,0,
8 ,8,0xe4,0,
24,0,0x9c,0,//inactive ego
24,8,0xac,0,
32,8,0xe4,0,
128
};

const unsigned char sprPauseResume[]={
0 ,0,0x6b,0,//r
8 ,0,0x84,0,//e
16,0,0x6c,0,//s
24,0,0x6e,0,//u
32,0,0x8c,0,//m
40,0,0x84,0,//e
128
};

const unsigned char sprPauseRestart[]={
0 ,8,0x6b,0,//r
8 ,8,0x84,0,//e
16,8,0x6c,0,//s
24,8,0x6d,0,//t
32,8,0x80,0,//a
40,8,0x6b,0,//r
48,8,0x6d,0,//t
128
};

const unsigned char sprPauseExit[]={
0 ,16,0x84,0,//e
8 ,16,0x7b,0,//x
16,16,0x88,0,//i
24,16,0x6d,0,//t
32,16,0x00,0,//space
40,16,0x86,0,//g
48,16,0x80,0,//a
56,16,0x8c,0,//m
64,16,0x84,0,//e
128
};

const unsigned char sprSoundTest[]={
0 ,0,0x6c,3,//s
8 ,0,0x85,3,//f
16,0,0x7b,3,//x
48,0,0x81,3,//b
56,0,0x86,3,//g
64,0,0x8c,3,//m
128
};

//update list for level clear text

const unsigned char levelClear[]={
0x20,0x4a,0x4b,//l top
0x20,0x4b,0x44,//e
0x20,0x4c,0x65,//v
0x20,0x4d,0x44,//e
0x20,0x4e,0x4b,//l
0x20,0x50,0x42,//c
0x20,0x51,0x4b,//l
0x20,0x52,0x44,//e
0x20,0x53,0x40,//a
0x20,0x54,0x61,//r
0x20,0x6a,0x5b,//l bottom
0x20,0x6b,0x54,//e
0x20,0x6c,0x75,//v
0x20,0x6d,0x54,//e
0x20,0x6e,0x5b,//l
0x20,0x70,0x52,//c
0x20,0x71,0x5b,//l
0x20,0x72,0x54,//e
0x20,0x73,0x50,//a
0x20,0x74,0x71 //r
};

//map array

unsigned char map[MAP_WDT*MAP_HGT];

//player vars

unsigned char player_x1;
unsigned char player_y1;
unsigned char player_x2;
unsigned char player_y2;
unsigned char player_x1_to;
unsigned char player_y1_to;
unsigned char player_x2_to;
unsigned char player_y2_to;
unsigned char player_x1e;
unsigned char player_y1e;
unsigned char player_dir;
unsigned char player_move_cnt;
unsigned char player_spr;
unsigned char player_spr_prev;
unsigned char player_atr;
unsigned char player_atr_dir;
unsigned char player_idle_cnt;
unsigned char player_exchange;
unsigned char player_tile;
unsigned char player_tile_bottom;
unsigned char player_sync_type;
unsigned char player_step;
unsigned char player_flash_cnt;

//enemy vars

unsigned char enemy_cnt;
unsigned char enemy_move_cnt;

unsigned char enemy_dir[ENEMY_MAX];
unsigned char enemy_x  [ENEMY_MAX];
unsigned char enemy_y  [ENEMY_MAX];
unsigned char enemy_atr[ENEMY_MAX];

//nametable update list for stats and items

unsigned char update_list_len;

unsigned char update_list[(ITEM_MAX+1)*3];//first entry is for falling bridge

//particles

unsigned char part_ptr;
unsigned char part_x  [PART_MAX];
unsigned char part_y  [PART_MAX];
unsigned char part_dy [PART_MAX];
unsigned char part_spr[PART_MAX];
unsigned char part_atr[PART_MAX];
unsigned char part_cnt[PART_MAX];

//general vars, global to work faster

unsigned char i,j;
unsigned char px,py;
unsigned char spr,atr;
unsigned int  i16,j16;
unsigned char pal_cnt;

//misc level vars

unsigned char frame_cnt;
unsigned char items_cnt;
unsigned char first_level;
unsigned char level;
unsigned char level_done;
unsigned char start_delay;
unsigned char restart;
unsigned char exchange;
unsigned char level_skip;
unsigned char level_clear_delay;
unsigned char pause;
unsigned char paused;
unsigned char music_prev;
unsigned char title_choice;
unsigned char title_level=1;
unsigned char music_muted;
unsigned char sound_muted;

/* Keep the title/pause sound switch effective without touching every call. */
static void sfx_out(unsigned char snd,unsigned char ch)
{
	if(!sound_muted) sfx_play(snd,ch);
}
#define sfx_play(snd,ch) sfx_out((snd),(ch))

unsigned char palette[32];



void fade_screen_in(const unsigned char *pal)
{
	for(i=0;i<16;i++)
	{
		ppu_waitnmi();
		if(!(i&3))
		{
			pal_fade_to_bg(pal);
			pal_fade_to_spr(pal);
		}
	}
}



void fade_screen_out(void)
{
	for(i=0;i<16;i++)
	{
		ppu_waitnmi();
		if(!(i&3)) pal_fade();
	}
}



/* fade_screen_in(palTitleBG) fades the sprite palettes to the same four rows it
 * fades the background to, which would make sprite palette 1 the same yellow
 * as background palette 1 and lose the grey title cursor.  Fade them to
 * palTitleSPR instead; those are also the SP0-SP3 rows in palettes/title.txt,
 * so the engine still recognises the title palette after a game. */
void fade_title_in(void)
{
	for(i=0;i<16;i++)
	{
		ppu_waitnmi();
		if(!(i&3))
		{
			pal_fade_to_bg(palTitleBG);
			pal_fade_to_spr(palTitleSPR);
		}
	}
}



/* 8x8 font tiles used by the original pause labels. */
static unsigned char menu_tile(char c)
{
	if(c>='A'&&c<='P') return (unsigned char)(0x80+c-'A');
	if(c>='0'&&c<='9') return (unsigned char)(0xf0+c-'0');
	switch(c)
	{
	case 'R': return 0x6b;
	case 'S': return 0x6c;
	case 'T': return 0x6d;
	case 'U': return 0x6e;
	case 'V': return 0x6f;
	case 'X': return 0x7b;
	default:  return 0x00;
	}
}

static void title_put_str(unsigned int base,unsigned char row,unsigned char col,const char *s)
{
	vram_adr(base+(unsigned int)row*32+col);
	while(*s) vram_put(menu_tile(*s++));
}

static void title_draw_text(unsigned char row,unsigned char col,const char *s)
{
	title_put_str(0x2000,row,col,s);
	title_put_str(0x2400,row,col,s);
}

/* The original title art gives the bottom half of attribute row 4 a
 * different palette, which made START GAME orange while the other menu
 * lines were blue.  Override just that bottom half in both nametables. */
static void title_set_menu_attrs(void)
{
	unsigned int base;

	for(base=0x23c0;base<=0x27c0;base+=0x400)
	{
		vram_adr(base+4*8+2); vram_put(0xf4);
		vram_adr(base+4*8+3); vram_put(0xf1);
		vram_adr(base+4*8+4); vram_put(0xfd);
	}
}

static void title_clear_row(unsigned char row,unsigned char col,unsigned char n)
{
	unsigned char k;
	for(k=0;k<n;k++) title_draw_text(row,(unsigned char)(col+k)," ");
}

static void title_draw_menu(void)
{
	/* The whole title scrolls eight pixels up, which keeps the logo's
	 * palette attributes intact.  Put the menu one tile row lower in the
	 * nametable so it stays at its original screen position.  Rows 22 and
	 * 23 also erase what remains of the old PRESS START art. */
	title_clear_row(19,10,13);
	title_clear_row(21,10,15);
	title_clear_row(22,10,15);
	title_clear_row(23,10,13);
	title_clear_row(25,10,13);
	title_draw_text(19,10,"START GAME");
	title_draw_text(21,10,"START LEVEL");
	title_draw_text(23,10,music_muted?"MUSIC OFF":"MUSIC ON");
	title_draw_text(25,10,sound_muted?"SOUND OFF":"SOUND ON");
	title_set_menu_attrs();
}

static void title_draw_level(void)
{
	char d[3];
	d[0]=(char)('0'+title_level/10);
	d[1]=(char)('0'+title_level%10);
	d[2]=0;
	title_draw_text(21,22,d);
}

/* The sound-test counters are sprites, exactly as on the NES: the selected
 * pair uses sprite palette 1 (index 3 is the title's pale yellow $38), the
 * other pair palette 2 (index 3 is $21, the same light blue as the menu
 * text), and both use $01 for the outline.  Sprites keep the digits out of
 * the background's 16x16 attribute blocks, so nothing else on row 23 changes
 * colour.  The title scrolls the background down by eight lines, so the
 * sprite must sit eight lines higher to share the row: row 23 starts at
 * scanline 184, an OAM y is the line above the first sprite line, and
 * 184-8-1 = 175.
 * These are the SP rows of palettes/title.txt, and fade_title_in() uploads
 * them, so the engine recognises the title palette when the game comes back
 * to the title screen (fade_screen_in() would upload the background rows here
 * instead, and the sprite colours would then not match title.txt).
 * Layout on row 23 (columns): 10 MUSIC ON/OFF, 20 SFX, 23 the SFX number,
 * 26 BGM, 29 the BGM number. */
static void title_draw_sound_values(void)
{
	oam_spr(184,175,0xf0+(px/10), (unsigned char)(j?2:1), 0);
	oam_spr(192,175,0xf0+(px%10),(unsigned char)(j?2:1), 1);
	oam_spr(232,175,0xf0+(py/10), (unsigned char)(j?1:2), 2);
	oam_spr(240,175,0xf0+(py%10),(unsigned char)(j?1:2), 3);
}


unsigned char check_map(unsigned char x,unsigned char y)
{
	i16= x    >>TILE_BIT;
	j16=(y-48)>>TILE_BIT;

	return map[(j16<<MAP_WDT_BIT)+i16];
}



void take_item(unsigned char x,unsigned char y)
{
	i16= x    >>TILE_BIT;
	j16=(y-48)>>TILE_BIT;
	i16+=(j16<<MAP_WDT_BIT);

	map[i16]=0;
	items_cnt--;

	part_x  [part_ptr]=x;
	part_y  [part_ptr]=y;
	part_dy [part_ptr]=-2;
	part_cnt[part_ptr]=16;
	part_atr[part_ptr]=3;

	i16+=0x20c0;
	y=i16>>8;
	x=i16&255;

	for(i=0;i<update_list_len;i+=3)
	{
		if(update_list[i]==y)
		{
			if(update_list[i+1]==x)
			{
				part_spr[part_ptr]=update_list[i+2];
				update_list[i+2]=0;
				break;
			}
		}
	}

	part_ptr=(part_ptr+1)&(PART_MAX-1);
}



void drop_bridge(void)
{
	i16= player_x1    >>TILE_BIT;
	j16=(player_y1-40)>>TILE_BIT;
	i16+=(j16<<MAP_WDT_BIT);

	map[i16]=0;

	i16+=0x20c0;

	update_list[0]=i16>>8;
	update_list[1]=i16&255;

	part_x  [part_ptr]=player_x1;
	part_y  [part_ptr]=player_y1+8;
	part_dy [part_ptr]=1;
	part_cnt[part_ptr]=8;
	part_spr[part_ptr]=0x1b;
	part_atr[part_ptr]=3;

	part_ptr=(part_ptr+1)&(PART_MAX-1);

	sfx_play(SFX_BRIDGE,0);
}



void update_stats(unsigned char show)
{
	py=show?23:240;

	oam_spr(30,py,0xe5+restart ,0,OAM_STATS+6);
	oam_spr(54,py,0xe5+exchange,0,OAM_STATS+7);
}



void credits_screen(void)
{
	unsigned int hold;	// j is an unsigned char, so it cannot hold 360 frames

	ppu_off();
	pal_clear();
	unrle_vram(credits,0x2000);
	scroll(0,8);
	ppu_on_bg();
	fade_title_in();

	hold=360;		// ~6 s at 60 Hz (was 150 = 2.5 s; ten lines need reading time)

	while(1)
	{
		ppu_waitnmi();
		i=pad_trigger();
			oam_spr(16,px&16?240:py,0xff,0,OAM_PAUSE);
			px++;
		hold--;
		if(!hold||(i&PAD_START)) break;
	}

	fade_screen_out();
}



void title_screen(void)
{
	ppu_off();
	pal_clear();
	oam_clear();
	unrle_vram(title,0x2000);
	unrle_vram(title,0x2400);

	/* The Vera title screen hides the old PRESS START prompt and uses
	 * the four menu buttons below the logo instead. */
	vram_adr(0x22ca);
	for(i=0;i<12;i++) vram_put(0);
	vram_adr(0x22ea);
	for(i=0;i<12;i++) vram_put(0);
	vram_adr(0x26ca);//erase text from second page
	for(i=0;i<12;i++) vram_put(0);
	vram_adr(0x26ea);
	for(i=0;i<12;i++) vram_put(0);

	title_choice=0;
	/* 0 is the hidden cow level; START GAME still forces level 1. */
	if(title_level>25) title_level=1;
	title_draw_menu();
	title_draw_level();

	scroll(256,8);
	ppu_on_all();

	music_play(musicData[MUS_TITLE]);
	if(music_muted) music_stop();

	fade_title_in();
	title_draw_menu();
	title_draw_level();

/* Returning from the sound test restarts the title menu here without
 * replaying the title art or the fade-in. */
title_menu_again:
	j=0;
	atr=16;
	frame_cnt=0;
	px=0;
	py=0;

	while(1)
	{
		ppu_waitnmi();

		scroll((frame_cnt&atr)?256:0,8);

		if(!j)
		{
			i=pad_trigger();

			/* Vera-style title buttons: UP/DOWN chooses a line,
			 * LEFT/RIGHT changes the level (0 = cow level) or toggles audio. */
			oam_spr(64,(unsigned char)(144+(title_choice<<4)),0xff,0,0);
			if(i&(PAD_UP|PAD_DOWN|PAD_A|PAD_B|PAD_LEFT|PAD_RIGHT))
			{
				if(i&(PAD_UP|PAD_A))   title_choice=(unsigned char)((title_choice+3)&3);
				if(i&(PAD_DOWN|PAD_B)) title_choice=(unsigned char)((title_choice+1)&3);
				if(title_choice==1 && (i&(PAD_LEFT|PAD_RIGHT)))
				{
					if((i&PAD_LEFT)&&title_level>0)  title_level--;
					if((i&PAD_RIGHT)&&title_level<25) title_level++;
					title_draw_level();
				}
				sfx_play(SFX_MENU,0);
			}
			if(i&(PAD_LEFT|PAD_RIGHT))
			{
				if(title_choice==2)
				{
					music_muted^=1;
					if(music_muted) music_stop();
					else music_play(musicData[MUS_TITLE]);
					title_draw_menu();
					title_draw_level();
					sfx_play(SFX_MENU,0);
				}
				else if(title_choice==3)
				{
					sound_muted^=1;
					title_draw_menu();
					title_draw_level();
					sfx_play(SFX_MENU,0);
				}
			}

			if(i)
			{
				if(code_str[px]!=i)
				
				{
					px=0;
				}
				else
				{
					px++;
					if(px==sizeof(code_str))
					{
						px=0;
						level_skip=1;
						sfx_play(SFX_MENU,0);
					}
				}
			}

			/* The original NES sound test needs A+B+Start.  The IIgs
			 * keyboard shim can only see one key code, so Tab (Select)
			 * opens the sound test directly instead of requiring a
			 * chord.  A second Tab collapses it back to the title
			 * menu; Start leaves it and starts the game. */
			if(i&PAD_SELECT)
			{
				py=1;
				frame_cnt=4;
				j=50;
				atr=4;
				/* Keep the menu visible; the sound-test readout is
				 * placed to the right of the MUSIC line.  Only the
				 * title cursor is cleared. */
				oam_clear();
				music_stop();
				sfx_play(SFX_MENU,0);
				continue;
			}

			if(i&PAD_START)
			{
				i=pad_poll();

				if(title_choice==2)
				{
					music_muted^=1;
					if(music_muted) music_stop();
					else music_play(musicData[MUS_TITLE]);
					title_draw_menu();
					title_draw_level();
					continue;
				}
				if(title_choice==3)
				{
					sound_muted^=1;
					title_draw_menu();
					title_draw_level();
					continue;
				}

				if(title_choice==1) first_level=title_level;
				else if(title_choice==0) first_level=1;
				if((i&PAD_A)&&(i&PAD_B)) py=1;
				if(i&PAD_SELECT) first_level=0;/* cow level! */
				frame_cnt=4;
				j=50;
				atr=4;
				music_stop();
				if(first_level==1)
				{
					sfx_play(SFX_START,0);
				}
				else
				{
					sfx_play(SFX_EXCHANGE, 0);
				}
			}
		}
		else
		{
			j--;
			if(!j) break;
		}

		frame_cnt++;
	}

	if(py)//sound test
	{
		unsigned char back_to_title=0;

		/* The readout shares row 23 with MUSIC ON/OFF.  The label keeps
		 * its normal column: "MUSIC ON" then has two blank columns
		 * before SFX, and "MUSIC OFF" has one, so the two never read as
		 * "OFFSFX".  SFX and BGM each carry their own two-digit value
		 * directly ("SFX00 BGM00"), so everything fits inside col 31. */
		title_clear_row(23,19,13);
		title_draw_text(23,20,"SFX");
		title_draw_text(23,26,"BGM");

		j=0;
		px=0;
		py=0;
		title_draw_sound_values();

		while(1)
		{
			ppu_waitnmi();
			title_draw_sound_values();
			i=pad_trigger();

			if(i&PAD_START) break;

			/* A second Tab closes the sound test and returns to the
			 * title menu instead of starting the game. */
			if(i&PAD_SELECT)
			{
				back_to_title=1;
				break;
			}

			if(i&PAD_LEFT)  j=0;
			if(i&PAD_RIGHT) j=1;

			if(i&PAD_UP)
			{
				if(!j) { if(px<SFX_ALL-1) px++; } else { if(py<MUS_ALL-1) py++; }
			}

			if(i&PAD_DOWN)
			{
				if(!j) { if(px) px--; } else { if(py) py--; }
			}

			/* Z stops the music; Space auditions the selected SFX or
			 * BGM (Space is the A button, so it works without touching
			 * X/Z).  X still auditions as well. */
			if((i&PAD_A) && !pad_space) music_stop();

			if((i&PAD_B) || ((i&PAD_A) && pad_space))
			{
				if(!j) sfx_play(px,0); else music_play(musicData[py]);
			}
		}

		if(back_to_title)
		{
			/* Erase the SFX/BGM readout and hide its sprites, restore
			 * the normal menu and resume the title music; do not run the
			 * fade-out path. */
			oam_clear();
			title_clear_row(23,19,13);
			title_draw_menu();
			title_draw_level();
			if(music_muted) music_stop();
			else music_play(musicData[MUS_TITLE]);
			goto title_menu_again;
		}
	}

	fade_screen_out();
	scroll(0,0);
}



void game_over_screen(void)
{
	ppu_off();
	pal_clear();
	unrle_vram(gameover,0x2000);
	/* Centre the GAME OVER art: its six text rows start at NES row 13. */
	scroll(0,28);
	ppu_on_bg();
	if(!music_muted) music_play(musicData[MUS_GAMEOVER]);
	fade_screen_in(palGameBG1);

	i16=10*50;

	while(1)
	{
		ppu_waitnmi();
		if(!i16||(pad_trigger()&PAD_START)) break;
		i16--;
	}

	music_stop();
	fade_screen_out();
}



void well_done_screen(void)
{
	ppu_off();
	pal_clear();
	oam_clear();
	unrle_vram(welldone,0x2000);
	unrle_vram(welldone,0x2400);

	vram_adr(0x2708);//erase text from second page
	for(i=0;i<17;i++) vram_put(0);
	vram_adr(0x2728);
	for(i=0;i<17;i++) vram_put(0);

	scroll(256-4,0);
	ppu_on_all();

	if(!music_muted) music_play(musicData[MUS_WELLDONE]);

	player_x1=16;
	player_x2=256-16-8;
	player_y1=152;
	player_y2=152;
	j=0;

	while(1)
	{
		ppu_waitnmi();

		if(!(frame_cnt&3))
		{
			pal_fade_to_bg(palWellDone);
			pal_fade_to_spr(palSprites);
		}

		if(frame_cnt>=50&&frame_cnt<58) player_y1--;
		if(frame_cnt>=58&&frame_cnt<66) player_y1++;
		if(frame_cnt>=100&&frame_cnt<108) player_y2--;
		if(frame_cnt>=108&&frame_cnt<116) player_y2++;

		oam_spr(player_x1,player_y1-8,PLAYER_SPR_IDLE     ,1|OAM_FLIP_H,0);//active ego
		oam_spr(player_x1,player_y1  ,PLAYER_SPR_IDLE+0x10,1|OAM_FLIP_H,1);

		i=rand();
		spr=PLAYER_SPR_ALTER+(i&3);
		atr=1+(i&0x40);

		oam_spr(player_x2,player_y2-8,spr     ,atr,2);//inactive ego
		oam_spr(player_x2,player_y2  ,spr+0x10,atr,3);

		scroll((frame_cnt&16)?256-4:-4,0);

		i=pad_trigger();

		if(!j&&(i&PAD_START))
		{
			j=20;
			sfx_play(SFX_MENU,0);
		}
		if(j)
		{
			j--;
			if(!j) break;
		}

		frame_cnt=(frame_cnt+1)&127;
	}

	music_stop();
	fade_screen_out();
	scroll(0,0);
}



void game_add_background(void)
{
	//draw screen borders

	setrand(level+1);

	vram_inc(0);

	vram_adr(0x20a1);
	vram_put(0x01);
	vram_put(0x02);
	vram_fill(0x03,26);
	vram_put(0x04);
	vram_put(0x01);

	vram_adr(0x2341);
	vram_put(0x01);
	vram_put(0x08);
	vram_fill(0x09,26);
	vram_put(0x0a);
	vram_put(0x01);

	vram_inc(1);

	vram_adr(0x20c1);
	vram_put(0x05);
	vram_fill(0x06,18);
	vram_put(0x07);
	vram_adr(0x20de);
	vram_put(0x0b);
	vram_fill(0x0c,18);
	vram_put(0x0d);

	vram_inc(0);

	//draw stars

	spr=rand()&7;

	for(j16=0;j16<20*32;j16+=32)
	{
		for(j=2;j<30;j++)
		{
			i16=(j16&~32)+(j&~1);

			if(!(map[i16]|map[i16+1]|map[i16+32]|map[i16+33]))
			{
				if(spr<8)
				{
					vram_adr(j16+j+0x20c0);
					vram_put(0xb8+spr);
				}

				spr+=1+(rand()&3);
				if(spr>30) spr=0;
			}
		}
	}
}



void game_set_palettes(void)
{
  memcpy(palette,level_ptrs[(level<<1)+1],16);
	memcpy(palette+16,palSprites,12);
	memcpy(palette+28,palette+12,4);
}



void game_loop(void)
{
	i=level<<1;

	ppu_waitnmi();
	ppu_off();
	pal_clear();
	oam_clear();
	unrle_vram(level_ptrs[i],0x2000);
	vram_read(map,0x20c0,MAP_WDT*MAP_HGT);
	game_add_background();
	ppu_on_all();

	i=MUS_GAME1+(level == 0 ? 0 : ((level - 1)/5));

	if(!music_muted&&music_prev!=i)
	{
		music_play(musicData[i]);
		music_prev=i;
	}

	enemy_cnt=0;
	enemy_move_cnt=8;
	update_list_len=0;
	items_cnt=0;
	i16=0;

	update_list[update_list_len++]=0;//falling bridge
	update_list[update_list_len++]=0;
	update_list[update_list_len++]=0;

	for(i=48;i<48+(MAP_HGT<<TILE_BIT);i+=TILE_SIZE)
	{
		for(j=0;j<MAP_WDT;j++)
		{
			spr=map[i16];

			switch(spr)
			{
			case TILE_NUM_PLAYER:
				player_x1=j<<TILE_BIT;
				player_y1=i;
				spr=0;
				break;

			case TILE_NUM_ENEMY_L:
			case TILE_NUM_ENEMY_R:
			case TILE_NUM_ENEMY_U:
			case TILE_NUM_ENEMY_D:
				if(spr==TILE_NUM_ENEMY_L) atr=2|OAM_FLIP_H; else atr=2;
				enemy_dir[enemy_cnt]  =spr;
				enemy_x  [enemy_cnt]  =j<<TILE_BIT;
				enemy_y  [enemy_cnt]  =i;
				enemy_atr[enemy_cnt++]=atr;
				spr=0;
				break;

			case TILE_NUM_ITEM_1:
			case TILE_NUM_ITEM_2:
				j16=0x20c0+i16;
				update_list[update_list_len++]=(j16>>8);
				update_list[update_list_len++]=(j16&255);
				update_list[update_list_len++]=(spr==TILE_NUM_ITEM_1?0xd0:0xd8);
				items_cnt++;
				break;
			}

			spr=tileType[spr];
			/* Keep the low two bits of the four water tiles so the
			 * animation can select the matching page-0 variant.  They
			 * are still TILE_WATER for every collision test. */
			if(spr==TILE_WATER) spr|=(map[i16]&3);
			map[i16++]=spr;
		}
	}

	for(i=0;i<PART_MAX;i++)
	{
		part_y[i]=255;
		part_cnt[i]=0;
	}
	part_ptr=0;

	set_vram_update(items_cnt+1,update_list);

	//show enemies, it is a copy of update code

	for(i=0;i<enemy_cnt;i++)//0 is OAM_ENEMY
	{
		j=enemy_dir[i];
		px=enemy_x[i];
		py=enemy_y[i];
		atr=enemy_atr[i];

		switch(j)
		{
		case TILE_NUM_ENEMY_L:
		case TILE_NUM_ENEMY_R:
			spr=(frame_cnt>>2)&3;
			oam_spr(px,py-8,0xb0+spr,atr,i);
			oam_spr(px,py  ,0xc0+spr,atr,ENEMY_MAX+i);
			break;

		case TILE_NUM_ENEMY_U:
		case TILE_NUM_ENEMY_D:
			spr=(frame_cnt>>4)&3;
			oam_spr(px,py-8,0xb4+spr,atr,i);
			oam_spr(px,py  ,0xc4+spr,atr,ENEMY_MAX+i);
			break;
		}
	}

	game_set_palettes();

	player_dir=DIR_NONE;
	player_move_cnt=8;
	player_spr=PLAYER_SPR_IDLE;
	player_spr_prev=player_dir;
	player_atr=1;//palette 1
	player_atr_dir=player_atr;
	player_idle_cnt=0;
	player_exchange=0;
	player_sync_type=level_params[(level<<1)+1];
	player_step=0;
	player_flash_cnt=0;

	start_delay=PLAYER_START_DELAY;
	level_done=DONE_NOTYET;
	level_clear_delay=0;
	exchange=level_params[level<<1];

	frame_cnt=0;
	pal_cnt=0;
	pause=0;
	paused=0;

	//stats are displayed with sprites

	oam_meta_spr(16,15,OAM_STATS,sprStats);

	update_stats(1);

	//main game logic loop

	while(!level_done)
	{
		ppu_waitnmi();
		if(paused)
		{
			// Cursor on the selected line (RESUME at 15, RESTART at 23).
			oam_spr(16,py,0xff,0,OAM_PAUSE);

			i=pad_trigger();
			j=0;
			if(i&PAD_START)
			{
				paused=0;
				pause=1;
				sfx_play(SFX_START,0);

				/* The last life is shown as 0 in the HUD.  RESTART would use
				 * that life and make the next death a game over immediately,
				 * so hide it and let EXIT take its place. */
				if(py==31||(!restart&&py==23))
				{
					level_done=DONE_EXIT;
					music_stop();
					music_prev=255;
					continue;
				}
				if(py==23)
				{
					level_done=DONE_RESTART;
					music_stop();
					music_prev=255;
				}
				else
				{
					// Restore the palette and the game sprites; the pause menu
					// is drawn entirely with sprites, so oam_clear() removes it.
					game_set_palettes();
					pal_all(palette);
					oam_clear();
					oam_meta_spr(16,15,OAM_STATS,sprStats);
					update_stats(1);
				}

				music_pause(0);
				continue;
			}

			/* Navigation stays active even when the HUD shows 0 lives;
			 * at that point RESTART is hidden and EXIT occupies its row. */
			if(((i&PAD_UP)||(i&PAD_A))&&py!=15)
			{
				sfx_play(SFX_MENU,0);
				if(py==31) py=restart?23:15;
				else py=15;
				px=0;
			}
			if(((i&PAD_DOWN)||(i&PAD_B))&&py!=31)
			{
				sfx_play(SFX_MENU,0);
				if(py==15) py=23;
				else if(py==23&&restart) py=31;
				px=0;
			}

			px++;
			continue;
		}

		if(pal_cnt<16)
		{
			if(!(pal_cnt&3)) pal_fade_to_all(palette);

			pal_cnt++;
		}

		//background tile animation

		/* The original toggles the NES background CHR bank every 16 frames.
		 * On the IIgs that forces a full-screen tile recompile; instead keep
		 * the bank fixed and rewrite only the four water tiles.  Their
		 * alternate CHR page is stored in free page-0 tiles $E1-$E4. */
		bank_bg(0);
		if(!(frame_cnt&15))
		{
			const unsigned char *mp;
			j=((frame_cnt>>4)&1)?1:0;
			/* Walk the map through a pointer: map[] indexing across a
			 * 256-byte boundary does not carry correctly in the generated
			 * 6502 code and would miss the water rows. */
			mp=map;
			for(i16=0;i16<MAP_WDT*MAP_HGT;i16++)
			{
				spr=*mp++;
				if((spr&TILE_WATER)==TILE_WATER)
				{
					vram_adr(0x20c0+i16);
					vram_put(j?(unsigned char)(0xe0+(spr&3)):(unsigned char)(0x1c+(spr&3)));
				}
			}
		}

		//sync alter ego

		if(!player_sync_type)
		{
			player_x2=248-player_x1;
			player_y2=player_y1;
			player_x2=MAX(16 ,player_x2);
			player_x2=MIN(240,player_x2);
		}
		else
		{
			player_x2=player_x1;
			player_y2=240-player_y1;
			player_y2=MAX(48 ,player_y2);
			player_y2=MIN(208,player_y2);
		}

		//draw player sprites to OAM

		if(player_idle_cnt==PLAYER_IDLE_MAX)
		{
			if(player_spr==PLAYER_SPR_FALL)   player_atr=player_atr_dir;
			if(player_spr!=PLAYER_SPR_LADDER) player_spr=PLAYER_SPR_IDLE;
		}

		/* Exchange flash: blink the ego sprites instead of recolouring them.
		 * The NES version flashed pal_col($3F15-$3F17) with $21/$27, but those
		 * entries alias onto SHR slots 3, 7 and 9 that the background palettes
		 * also fill (BG2 uses 0,7,8,9, SP1 uses 0,3,7,9), so the flash put
		 * stripes in the sea.  Switching the OAM palette bits fixed the sea but
		 * painted the ego with sprite palette 3 ($16/$32/$30 = red head, white
		 * body) and could leave it there after the swap.  Blinking keeps the
		 * ego's own colours (white head, blue clothes) for the whole move. */
		if(player_flash_cnt) player_flash_cnt--;

		if((!start_delay||(start_delay&8))&&(!player_flash_cnt||(frame_cnt&1)))
		{
			oam_spr(player_x1,player_y1-8,player_spr     ,player_atr,OAM_PLAYER+0);//active ego
			oam_spr(player_x1,player_y1  ,player_spr+0x10,player_atr,OAM_PLAYER+1);

			if(!level_clear_delay) i=rand(); else i=0;

			spr=PLAYER_SPR_ALTER+(i&3);
			atr=1+(i&0x40);
			oam_spr(player_x2,player_y2-8,spr     ,atr,OAM_PLAYER+2);//inactive ego
			oam_spr(player_x2,player_y2  ,spr+0x10,atr,OAM_PLAYER+3);
		}
		else
		{
			oam_spr(0,255,0,0,OAM_PLAYER+0);//hide player sprites
			oam_spr(0,255,0,0,OAM_PLAYER+1);
			oam_spr(0,255,0,0,OAM_PLAYER+2);
			oam_spr(0,255,0,0,OAM_PLAYER+3);
		}

		//items animation

		j=((frame_cnt>>1)&7);

		for(i=5;i<update_list_len;i+=3)
		{
			spr=update_list[i];
			if(spr) update_list[i]=(spr&~7)|j;
			j=(j+1)&7;
		}

		//particles animation

		for(i=0;i<PART_MAX;i++)
		{
			oam_spr(part_x[i],part_y[i],part_spr[i],part_atr[i],OAM_PARTS+i);

			if(part_cnt[i])
			{
				part_y[i]+=part_dy[i];
				part_cnt[i]--;
				if(!part_cnt[i]) part_y[i]=255;//hide particle
			}
		}

		//enemy and player aren't moving at the start or end of a level

		if(start_delay)
		{
			start_delay--;
			continue;
		}

		if(level_clear_delay)
		{
			level_clear_delay--;
			if(!level_clear_delay) level_done=DONE_CLEAR;
			continue;
		}

		//check gamepad, do actions and game logic

		i=pad_poll();

		if((i&PAD_SELECT)&&level_skip)
		{
			level_clear_delay=PLAYER_CLEAR_DELAY;
			continue;
		}

		if((i&PAD_START)&&!pause&&!paused)//pause menu
		{
			paused=1;
			pause=1;
			music_pause(1);
			sfx_play(SFX_START,0);
			for(j=0;j<2;j++)
			{
				for(i=0;i<32;i++)
				{
					if(i<4||(i>=16&&i<20)) continue;
					if(palette[i]>=0x10) palette[i]-=0x10; else palette[i]=0x0f;
					if(!palette[i]) palette[i]=0x0f;
				}
			}
			pal_all(palette);
			oam_clear();
			oam_meta_spr(24,15 ,OAM_PAUSE+1,sprPauseResume);
			if(restart) oam_meta_spr(24,15 ,OAM_PAUSE+7,sprPauseRestart);
			oam_meta_spr(24,restart?15:7 ,OAM_PAUSE+14,sprPauseExit);
			px=0;
			py=15;
			continue;
		}
		else
		{
			if(!(i&PAD_START)) pause=0;
		}

		if(player_spr==PLAYER_SPR_FALL&&player_spr_prev!=PLAYER_SPR_FALL)
		{
			sfx_play(SFX_FALLING,0);
		}
		if(player_spr!=PLAYER_SPR_FALL&&player_spr_prev==PLAYER_SPR_FALL)
		{
			sfx_play(SFX_DROP,0);
		}
		player_spr_prev=player_spr;

		if(player_exchange==1)
		{
			if(player_x1<player_x1_to) player_x1=MIN(player_x1_to,player_x1+4);
			if(player_x1>player_x1_to) player_x1=MAX(player_x1_to,player_x1-4);
			if(player_y1<player_y1_to) player_y1=MIN(player_y1_to,player_y1+4);
			if(player_y1>player_y1_to) player_y1=MAX(player_y1_to,player_y1-4);
			if(player_x2<player_x2_to) player_x2=MIN(player_x2_to,player_x2+4);
			if(player_x2>player_x2_to) player_x2=MAX(player_x2_to,player_x2-4);
			if(player_y2<player_y2_to) player_y2=MIN(player_y2_to,player_y2+4);
			if(player_y2>player_y2_to) player_y2=MAX(player_y2_to,player_y2-4);

			player_flash_cnt=2;

			if(player_x1==player_x1_to&&player_y1==player_y1_to&&
			   player_x2==player_x2_to&&player_y2==player_y2_to)
			   {
					if(check_map(player_x1,player_y1)&TILE_LADDER)
					{
						player_spr=PLAYER_SPR_LADDER;
					}
					else
					{
						player_spr=PLAYER_SPR_WALK;
					}

					player_exchange=2;
			   }
		}
		else
		{
			if(player_dir==DIR_NONE)
			{
				player_tile=check_map(player_x1,player_y1);
				player_tile_bottom=check_map(player_x1,player_y1+8);

				if(player_exchange!=1)//taking items has priority over exchange
				{
					if(player_tile&TILE_ITEM1)
					{
						take_item(player_x1,player_y1);
						sfx_play(SFX_ITEM1,2);
						i=0;
					}

					if(check_map(player_x2,player_y2)&TILE_ITEM2)
					{
						take_item(player_x2,player_y2);
						sfx_play(SFX_ITEM2,2);
						i=0;
					}

					if(!items_cnt)
					{
						level_clear_delay=PLAYER_CLEAR_DELAY;
						continue;
					}
				}

				if(i&(PAD_A|PAD_B))
				{
					if(!player_exchange)
					{
						if(exchange)
						{
							if(!(check_map(player_x2,player_y2)&TILE_WALL))
							{
								player_x1_to=player_x2;
								player_y1_to=player_y2;
								player_x2_to=player_x1;
								player_y2_to=player_y1;
								exchange--;
								update_stats(1);
								sfx_play(SFX_EXCHANGE,2);
								player_exchange=1;
							}
							else
							{
								sfx_play(SFX_NO_EXCHANGE,2);
								player_exchange=2;
								player_flash_cnt=10;
							}
						}
						else
						{
							sfx_play(SFX_OUT_OF_EXCHANGES,2);
							player_exchange=2;
						}
					}
				}
				else
				{
					player_exchange=0;
				}

				if(player_exchange!=1)
				{
					if(player_tile&TILE_WATER)
					{
						level_done=DONE_NOLUCK;
						continue;
					}

					if(!(player_tile_bottom&TILE_FLOOR)&&!(player_tile&TILE_LADDER))
					{
						player_dir=DIR_DOWN;
						player_move_cnt=8;
						player_idle_cnt=PLAYER_IDLE_MAX-1;
						player_spr=PLAYER_SPR_FALL;
						i=0;//no control available mid-air
					}

					if(i&PAD_LEFT)
					{
						if(!(check_map(player_x1-8,player_y1)&TILE_WALL))
						{
							player_dir=DIR_LEFT;
							player_move_cnt=8;
							player_idle_cnt=0;
							sfx_play(player_step?SFX_WALK2:SFX_WALK1,1);
							player_step^=1;

							if(player_tile_bottom&TILE_BRIDGE) drop_bridge();
						}
					}

					if(i&PAD_RIGHT)
					{
						if(!(check_map(player_x1+8,player_y1)&TILE_WALL))
						{
							player_dir=DIR_RIGHT;
							player_move_cnt=8;
							player_idle_cnt=0;
							sfx_play(player_step?SFX_WALK2:SFX_WALK1,1);
							player_step^=1;

							if(player_tile_bottom&TILE_BRIDGE) drop_bridge();
						}
					}

					if(player_tile&TILE_LADDER)
					{
						if(i&PAD_UP)
						{
							if(check_map(player_x1,player_y1-8)&TILE_LADDER)
							{
								player_dir=DIR_UP;
								player_move_cnt=8;
								player_idle_cnt=0;
								player_spr=PLAYER_SPR_LADDER;
								sfx_play(SFX_LADDER,1);
							}
						}
					}

					if((player_tile&TILE_LADDER)||(player_tile_bottom&TILE_LADDER))
					{
						if(i&PAD_DOWN)
						{
							if(!(player_tile_bottom&(TILE_WALL|TILE_BRIDGE)))
							{
								player_dir=DIR_DOWN;
								player_move_cnt=8;
								player_idle_cnt=0;
								player_spr=PLAYER_SPR_LADDER;
								sfx_play(SFX_LADDER,1);
							}
						}
					}

					if(player_dir==DIR_NONE)
					{
						if(player_idle_cnt<PLAYER_IDLE_MAX) player_idle_cnt++;
					}
				}
			}

			if(player_dir!=DIR_NONE)
			{
				switch(player_dir)
				{
				case DIR_LEFT:
					player_x1--;
					player_spr=PLAYER_SPR_WALK+(3-((player_x1>>1)&3));
					player_atr=1;
					player_atr_dir=player_atr;
					break;

				case DIR_RIGHT:
					player_x1++;
					player_spr=PLAYER_SPR_WALK+((player_x1>>1)&3);
					player_atr=1|OAM_FLIP_H;
					player_atr_dir=player_atr;
					break;

				case DIR_UP:
					player_y1--;
					player_atr=1|((player_y1<<4)&OAM_FLIP_H);
					break;

				case DIR_DOWN:
					player_y1++;
					player_atr=1|((player_y1<<4)&OAM_FLIP_H);
					break;
				}

				player_move_cnt--;

				if(!player_move_cnt)
				{
					if(player_y1>=200) level_done=DONE_NOLUCK;
					player_dir=DIR_NONE;
				}
			}
		}

		frame_cnt++;

		if(frame_cnt&1||player_exchange==1) continue;//move enemies every other frame, stop on exchange

		//process enemy movement logic and draw them to OAM

		player_x1e=player_x1+8;
		player_y1e=player_y1+8;

		for(i=0;i<enemy_cnt;i++)//0 is OAM_ENEMY
		{
			j=enemy_dir[i];
			px=enemy_x[i];
			py=enemy_y[i];
			atr=enemy_atr[i];

			if(py>=player_y1&&py<player_y1e)
			{
				if(px>=player_x1&&px<player_x1e)
				{
					level_done=DONE_NOLUCK;
				}
			}

			switch(j)
			{
			case TILE_NUM_ENEMY_L:
			case TILE_NUM_ENEMY_R:
				spr=(frame_cnt>>2)&3;
				oam_spr(px,py-8,0xb0+spr,atr,i);
				oam_spr(px,py  ,0xc0+spr,atr,ENEMY_MAX+i);
				break;

			case TILE_NUM_ENEMY_U:
			case TILE_NUM_ENEMY_D:
				spr=(frame_cnt>>4)&3;
				oam_spr(px,py-8,0xb4+spr,atr,i);
				oam_spr(px,py  ,0xc4+spr,atr,ENEMY_MAX+i);
				break;
			}

			switch(j)
			{
			case TILE_NUM_ENEMY_L: enemy_x[i]--; break;
			case TILE_NUM_ENEMY_R: enemy_x[i]++; break;
			case TILE_NUM_ENEMY_U: enemy_y[i]--; break;
			case TILE_NUM_ENEMY_D: enemy_y[i]++; break;
			}
		}

		enemy_move_cnt--;

		if(!enemy_move_cnt)
		{
			for(i=0;i<enemy_cnt;i++)
			{
				px=enemy_x[i];
				py=enemy_y[i];

				switch(enemy_dir[i])
				{
				case TILE_NUM_ENEMY_L:
					if(!(check_map(px-8,py+8)&TILE_FLOOR)||
					    (check_map(px-8,py)  &TILE_WALL))
					{
						enemy_dir[i]=TILE_NUM_ENEMY_R;
						enemy_atr[i]=2;
					}
					break;

				case TILE_NUM_ENEMY_R:
					if(!(check_map(px+8,py+8)&TILE_FLOOR)||
					    (check_map(px+8,py)  &TILE_WALL))
					{
						enemy_dir[i]=TILE_NUM_ENEMY_L;
						enemy_atr[i]=2|OAM_FLIP_H;
					}
					break;

				case TILE_NUM_ENEMY_U:
					if(check_map(px,py-8)&(TILE_WALL|TILE_BRIDGE|TILE_WATER))
					{
						enemy_dir[i]=TILE_NUM_ENEMY_D;
					}
					break;

				case TILE_NUM_ENEMY_D:
					if(check_map(px,py+8)&(TILE_WALL|TILE_BRIDGE|TILE_WATER))
					{
						enemy_dir[i]=TILE_NUM_ENEMY_U;
					}
					break;
				}
			}

			enemy_move_cnt=8;
		}

		//palette animation for eyes of enemies

		i=(frame_cnt>>4)&3;
		if(i==3) i=1;
		pal_col(25,6+(i<<4));
	}

	i=0;

	if(level_done==DONE_CLEAR)
	{
		sfx_play(SFX_LEVEL_CLEAR,0);

		set_vram_update(0,0);
		ppu_waitnmi();

		j=0;
		for(i=0;i<20;i++)
		{
			update_list[j++]=0x20;
			update_list[j++]=0x4a+i;
			update_list[j++]=0;
		}
		set_vram_update(20,update_list);
		ppu_waitnmi();

		j=1;
		for(i=1;i<20;i++)
		{
			update_list[j]=0x6a+i;
			j+=3;
		}
		ppu_waitnmi();

		oam_meta_spr(16,240,OAM_STATS  ,sprStats);		//hide stats
		update_stats(0);
		memcpy(update_list,levelClear,sizeof(levelClear));

		for(i=0;i<150-PLAYER_CLEAR_DELAY;i++)
		{
			ppu_waitnmi();

			if((i&15)==9) for(j=2;j<20*3;j+=3) update_list[j]=0;
			if((i&15)==1) memcpy(update_list,levelClear,sizeof(levelClear));
		}

		if(level==5||level==10||level==15||level==20||level==25) i=1; else i=0;
	}

	if(level_done==DONE_NOLUCK)
	{
		sfx_play(SFX_HIT,0);

		/* Drowning flash: blink the ego sprites, same reasoning as the exchange
		 * flash above -- no palette writes, so the background stays put and the
		 * ego keeps its own colours. */
		for(i=0;i<50;i++)
		{
			ppu_waitnmi();
			if(i&4)
			{
				oam_spr(0,255,0,0,OAM_PLAYER+0);
				oam_spr(0,255,0,0,OAM_PLAYER+1);
			}
			else
			{
				oam_spr(player_x1,player_y1-8,player_spr     ,player_atr,OAM_PLAYER+0);
				oam_spr(player_x1,player_y1  ,player_spr+0x10,player_atr,OAM_PLAYER+1);
			}
		}

		i=1;
		music_prev=255;
	}

	set_vram_update(0,0);
	if(i) music_stop();
	fade_screen_out();
}



void main(void)
{
	level_skip=0;
  first_level = 1;

	credits_screen();

	while(1)
	{
		title_screen();

		level=first_level;
		restart=5;
		music_prev=255;

		while(restart!=255)
		{
			game_loop();

			switch(level_done)
			{
			case DONE_CLEAR:
				level++;

				if(level==5||level==10||level==15||level==20)
				{
					if(restart<9) restart++;
				}

				if(level==26)
				{
					restart=255;
					well_done_screen();//game clear
				}
				break;

			case DONE_EXIT:
				restart=255;
				break;

			case DONE_RESTART:
			case DONE_NOLUCK:
				restart--;
				if(restart==255) game_over_screen();
				break;
			}
		}
	}
}
