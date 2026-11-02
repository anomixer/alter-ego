/* Apple II VERA runtime for the NES Alter Ego game. */
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdlib.h>
#include "music.h"


#define PAD_A      0x01
#define PAD_B      0x02
#define PAD_SELECT 0x04
#define PAD_START  0x08
#define PAD_UP     0x10
#define PAD_DOWN   0x20
#define PAD_LEFT   0x40
#define PAD_RIGHT  0x80
#define ENEMY_MAX  8
#define TILE_WALL  0x01
#define TILE_LADDER 0x02
#define TILE_ITEM1 0x04
#define TILE_ITEM2 0x08
#define TILE_BRIDGE 0x10
#define TILE_WATER 0x20
#define TILE_FLOOR (TILE_WALL|TILE_LADDER|TILE_BRIDGE)
#define ITEM_MAX 20
#define ENEMY_RIGHT 0x21
#define ENEMY_LEFT  0x22
#define ENEMY_UP    0x23
#define ENEMY_DOWN  0x24

#ifndef VERA_BASE
#define VERA_BASE 0xC200
#endif
#define VERA_DC_VID (*(volatile uint8_t*)(VERA_BASE+0x09))
#define KEYBOARD    (*(volatile uint8_t*)0xC000)
#define KBDSTRB     (*(volatile uint8_t*)0xC010)
#define VERA_ADDR_L (*(volatile uint8_t*)(VERA_BASE+0x00))
#define VERA_ADDR_M (*(volatile uint8_t*)(VERA_BASE+0x01))
#define VERA_ADDR_H (*(volatile uint8_t*)(VERA_BASE+0x02))
#define VERA_DATA0  (*(volatile uint8_t*)(VERA_BASE+0x03))
#define VERA_L0_MAP (*(volatile uint8_t*)(VERA_BASE+0x0E))
#define VERA_L0_TIL (*(volatile uint8_t*)(VERA_BASE+0x0F))
#define VERA_L0_HSC_L (*(volatile uint8_t*)(VERA_BASE+0x10))
#define VERA_L0_HSC_H (*(volatile uint8_t*)(VERA_BASE+0x11))
#define VERA_IEN    (*(volatile uint8_t*)(VERA_BASE+0x06))
#define VERA_ISR    (*(volatile uint8_t*)(VERA_BASE+0x07))

extern void __fastcall__ vera_oam_init(void);
extern void joystick_init(void);
extern uint8_t joystick_pad(void);
extern uint8_t __fastcall__ sound_test_edge(uint8_t pad);
extern void __fastcall__ vera_oam_present(void);
extern uint8_t __fastcall__ oam_spr(uint8_t x, uint8_t y, uint8_t tile,
                                    uint8_t attr, uint8_t id);
extern uint8_t __fastcall__ oam_meta_spr(uint8_t x, uint8_t y, uint8_t id,
                                         const uint8_t *data);
extern const uint8_t title_map_rle[];
extern const uint8_t title_screen_prompt[];
extern const uint8_t title_screen_palette[256];

static uint8_t player_x,player_y,sync_type;
static uint8_t enemy_x[ENEMY_MAX],enemy_y[ENEMY_MAX];
static uint8_t enemy_dir[ENEMY_MAX],enemy_attr[ENEMY_MAX],enemy_count;
static uint8_t collision_map[640],items_left;
static uint16_t item_map_offset[ITEM_MAX];
#ifdef FTM_VERA
#pragma bss-name (push, "FTM_EXTRA_BSS")
#endif
static uint16_t item_cell[ITEM_MAX];
#ifdef FTM_VERA
#pragma bss-name (pop)
#endif
#ifdef FTM_VERA
#pragma bss-name (push, "FTM_HIGH_BSS")
#endif
static uint8_t item_base[ITEM_MAX],item_count;
#ifdef FTM_VERA
#pragma bss-name (pop)
#pragma bss-name (push, "FTM_EXTRA_BSS")
#endif
static uint8_t particle_x[4],particle_y[4],particle_tile[4],particle_dy[4];
static uint8_t particle_frames[4],particle_next;
#ifdef FTM_VERA
#pragma bss-name (pop)
#endif
static uint8_t frame_count,enemy_move_count,player_fall_steps;
static uint8_t player_move_steps,player_move_dir;
static uint8_t player_step;
static uint8_t player_facing_right,player_ladder_pose,player_ladder_flip;
static uint8_t player_is_falling;
static uint8_t player_idle_frames,player_walk_tile;
static uint8_t player_flash_frames,ego_colour_state,eye_state;
#ifdef FTM_VERA
#pragma bss-name (push, "FTM_EXTRA_BSS")
#endif
static uint8_t level_palette[64],pause_palette[64],fade_palette[64];
#ifdef FTM_VERA
#pragma bss-name (pop)
#endif
static uint8_t level_fade_frame;
static uint8_t bridge_dropped;
static uint8_t alter_anim_state=0xA5;
static uint8_t exchange_left,exchange_active,exchange_x,exchange_y;
static uint8_t exchange_input_lock;
static uint8_t player_dead,death_frames;
static uint8_t lives_remaining=5,game_over;
static uint8_t gameover_music_started;
static uint16_t gameover_timer;
static uint8_t level_clear_timer,level_cleared;
static uint8_t clear_display_timer;
static uint8_t start_delay;
static uint8_t credits_visible;
static uint8_t paused,pause_choice,pause_frames;
uint8_t pause_last_dirs;
static uint8_t pause_move_cooldown;
static uint8_t current_level=1;
static uint8_t active_music=255;
static uint8_t music_muted;
static uint8_t sound_muted,title_menu_dirty;
static uint8_t title_code_index,level_skip;
static uint8_t title_choice,title_level=1;
static uint8_t keyboard_model,keyboard_last_pad,keyboard_last_held;
static uint8_t keyboard_mute_down,keyboard_sound_down;

#define MOVE_NONE 0
#define MOVE_LEFT 1
#define MOVE_RIGHT 2
#define MOVE_UP 3
#define MOVE_DOWN 4

static void draw_scene_sprites(void);
static uint8_t keyboard_pad(void);
static void keyboard_level_reset(void);
static uint8_t load_level_file(uint8_t level);
static uint8_t load_raw_asset(const char *name,uint16_t address,uint8_t high,
                              uint16_t size);
static void sound_test_screen(void);
static void hide_pause_sprites(void);
static void leave_game_to_title(void);
static void set_level_palette(uint8_t dim);
static void update_ego_colour(void);
static void update_enemy_eyes(void);
static void loading_tick(void);
static void palette_scale(const uint8_t *p,uint8_t scale);
static void fade_out(void);
static void get_alter_position(uint8_t *x,uint8_t *y);

static void stop_music(void)
{
    music_stop();
    active_music=255;
}

static void play_music(uint8_t track)
{
    if (active_music!=track) {
        music_start(track);
        active_music=track;
    }
}

static uint8_t level_music(uint8_t level)
{
#ifdef FTM_VERA
    /* Native slot 3 duplicates slot 2; the following themes are at 4-6. */
    static const uint8_t tracks[5]={1,2,4,5,6};
#else
    /* The PSG pack has a separate Level 2 entry before the game's Alt theme. */
    static const uint8_t tracks[5]={1,3,4,5,6};
#endif
    if (!level) return 1;
    return tracks[(level-1)/5];
}

static void prefetch_next_level_music(void)
{
    uint8_t next;
    if (current_level>=25) return;
    next=level_music((uint8_t)(current_level+1));
    if (!music_muted && next!=active_music) music_prefetch(next);
}

/* NES bank_bg toggles the two 4KB background CHR pages every 16 frames.
 * VERA holds those pages in separate 8KB tile sets; hardware sprites keep
 * using the primary set at $10000. */
static void animate_background(void)
{
    VERA_L0_TIL=(frame_count&0x10)?0x90:0x80;
}

/* NES assigns each item an independently phased eight-frame CHR sequence,
 * starting at $D0 for ITEM1 and $D8 for ITEM2. */
static void animate_items(void)
{
    uint8_t i,frame=(uint8_t)((frame_count>>1)&7);
    if (frame_count&1) return;
    for (i=0; i<item_count; ++i) {
        if (collision_map[item_cell[i]]&(TILE_ITEM1|TILE_ITEM2)) {
            uint16_t address=item_map_offset[i];
            VERA_ADDR_L=(uint8_t)address;
            VERA_ADDR_M=(uint8_t)(address>>8);
            VERA_ADDR_H=0x10;
            VERA_DATA0=(uint8_t)(item_base[i]|((frame+i)&7));
        }
    }
}

/* NES take_item() emits a 16-frame particle that rises two pixels each frame. */
static void advance_item_particles(void)
{
    uint8_t i;
    for (i=0; i<4; ++i) {
        if (particle_frames[i]) {
            particle_y[i]=(uint8_t)(particle_y[i]+particle_dy[i]);
            if (!--particle_frames[i]) particle_y[i]=240;
        }
    }
}

static void draw_level_clear(uint8_t visible)
{
    static const uint8_t top[11]={0x4B,0x44,0x65,0x44,0x4B,0,
                                   0x42,0x4B,0x44,0x40,0x61};
    static const uint8_t bottom[11]={0x5B,0x54,0x75,0x54,0x5B,0,
                                      0x52,0x5B,0x54,0x50,0x71};
    uint8_t col;
    uint16_t address;
    /* NES clears both 20-cell title rows before drawing LEVEL CLEAR.
     * Clear the full range on each blink so the old level name stays gone. */
    for (col=0; col<20; ++col) {
        address=(uint16_t)((2*64+10+col+4)*2);
        VERA_ADDR_L=(uint8_t)address;
        VERA_ADDR_M=(uint8_t)(address>>8);
        VERA_ADDR_H=0x20; /* advance 2 bytes: leave tile palette attrs intact */
        VERA_DATA0=(visible && col<11)?top[col]:0;
        address=(uint16_t)((3*64+10+col+4)*2);
        VERA_ADDR_L=(uint8_t)address;
        VERA_ADDR_M=(uint8_t)(address>>8);
        VERA_ADDR_H=0x20;
        VERA_DATA0=(visible && col<11)?bottom[col]:0;
    }
}

static void wait_frame(void)
{
    while (!(VERA_ISR&0x01)) {}
    VERA_ISR=0x01; /* VERA IRQ status is write-one-to-clear. */
}

static void vera_sync_init(void)
{
    VERA_IEN=0;
    VERA_ISR=0x0F; /* Clear pending VERA interrupt status. */
    VERA_IEN=0x01; /* Enable VSYNC status for frame pacing. */
}

static void write_map_rle(const uint8_t *src,uint8_t base)
{
    uint16_t out=0;
    VERA_ADDR_L=0;
    VERA_ADDR_M=base;
    VERA_ADDR_H=0x10;
    while (out<4096) {
        uint8_t control=*src++,count;
        if (control&0x80) {
            uint8_t value=*src++;
            count=(uint8_t)((control&0x7F)+3);
            while (count-- && out<4096) { VERA_DATA0=value; ++out; }
        } else {
            count=(uint8_t)(control+1);
            while (count-- && out<4096) { VERA_DATA0=*src++; ++out; }
        }
    }
}

static void upload_palette(const uint8_t *src)
{
    uint16_t i;
    VERA_ADDR_L=0;
    VERA_ADDR_M=0xFA;
    VERA_ADDR_H=0x11;
    for (i=0; i<256; ++i) VERA_DATA0=src[i];
}

static void set_title_prompt(uint8_t visible)
{
    const uint8_t *p=title_screen_prompt;
    uint8_t n=*p++;
    while (n--) {
        uint8_t lo=*p++,hi=*p++,tile=*p++;
        VERA_ADDR_L=lo;
        VERA_ADDR_M=(uint8_t)(0x20+hi);
        VERA_ADDR_H=0x10;
        VERA_DATA0=visible?tile:0;
    }
}

static void title_map_cell(uint8_t col,uint8_t row,uint8_t tile,uint8_t palette)
{
    uint16_t offset=(uint16_t)(((uint16_t)row*64u+col+4u)*2u);
    VERA_ADDR_L=(uint8_t)offset;
    VERA_ADDR_M=(uint8_t)(0x20+(offset>>8));
    VERA_ADDR_H=0x10;
    VERA_DATA0=tile;
    VERA_DATA0=(uint8_t)(palette<<4);
}

/* The title CHR contains 8x16 uppercase glyphs: A-P use $40/$50 pairs and
 * Q-Z use $60/$70 pairs. Digits use the existing 8x8 $F0-$F9 sprite font. */
static void title_map_text(const char *text,uint8_t col,uint8_t row,
                           uint8_t palette)
{
    while (*text) {
        uint8_t ch=(uint8_t)*text++,top=0,bottom=0;
        if (ch>='A' && ch<='P') top=(uint8_t)(0x40+ch-'A');
        else if (ch>='Q' && ch<='Z') top=(uint8_t)(0x60+ch-'Q');
        if (top) bottom=(uint8_t)(top+0x10);
        else if (ch>='0' && ch<='9') top=(uint8_t)(0xF0+ch-'0');
        title_map_cell(col,row,top,palette);
        title_map_cell(col,(uint8_t)(row+1),bottom,palette);
        ++col;
    }
}

static void title_map_clear_text(uint8_t col,uint8_t row,uint8_t width)
{
    while (width--) {
        title_map_cell(col,row,0,0);
        title_map_cell(col,(uint8_t)(row+1),0,0);
        ++col;
    }
}

/* Menu navigation changes only palette attributes, not the glyph tiles. */
static void title_map_palette(uint8_t row,uint8_t palette)
{
    uint8_t line,col;
    uint16_t offset;
    for (line=0;line<2;line++) {
        offset=(uint16_t)(((uint16_t)(row+line)*64u+14u)*2u+1u);
        VERA_ADDR_L=(uint8_t)offset;
        VERA_ADDR_M=(uint8_t)(0x20+(offset>>8));
        VERA_ADDR_H=0x20; /* advance to the next cell's attribute */
        for (col=0;col<13;col++) VERA_DATA0=(uint8_t)(palette<<4);
    }
}

static void redraw_title_audio(void)
{
    title_map_clear_text(10,23,12);
    title_map_clear_text(10,25,12);
    title_map_text(music_muted?"MUSIC OFF":"MUSIC ON",10,23,title_choice==2?3:0);
    title_map_text(sound_muted?"SOUND OFF":"SOUND ON",10,25,title_choice==3?3:0);
    title_menu_dirty=0;
}

static void set_start_option_visible(uint8_t visible)
{
    if (title_choice==0) {
        if (visible) title_map_text("START GAME",10,19,3);
        else title_map_clear_text(10,19,12);
    } else if (title_choice==1) {
        if (visible) {
            char digits[3];
            digits[0]=(char)('0'+title_level/10);
            digits[1]=(char)('0'+title_level%10);
            digits[2]=0;
            title_map_text("START LEVEL",10,21,3);
            title_map_text(digits,21,21,3);
        } else title_map_clear_text(10,21,13);
    }
}

static void draw_title_menu(void)
{
    uint8_t game_palette=title_choice==0?3:0;
    uint8_t level_palette=title_choice==1?3:0;
    uint8_t music_palette=title_choice==2?3:0;
    uint8_t sound_palette=title_choice==3?3:0;
    char digits[3];
    title_map_clear_text(10,19,12);
    title_map_clear_text(10,21,12);
    title_map_clear_text(10,23,12);
    title_map_clear_text(10,25,12);
    title_map_text("START GAME",10,19,game_palette);
    title_map_text("START LEVEL",10,21,level_palette);
    title_map_text(music_muted?"MUSIC OFF":"MUSIC ON",10,23,music_palette);
    title_map_text(sound_muted?"SOUND OFF":"SOUND ON",10,25,sound_palette);
    digits[0]=(char)('0'+title_level/10);
    digits[1]=(char)('0'+title_level%10);
    digits[2]=0;
    /* Center the small 8x8 digits vertically beside the 8x16 label. */
    title_map_text(digits,21,21,level_palette);
    title_menu_dirty=0;
}

/* Show the title menu. Direction changes are edge-triggered so a held
 * Apple IIe key does not race through levels; the II+ latch is cleared after
 * each menu direction so repeated key presses work there too. */
static void title_screen(void)
{
    uint8_t title_guard=60,pad,sound_test=0,last_dirs=0,dirs,new_dirs;
    uint8_t old_choice,old_level;
    static const uint8_t code[6]={PAD_B,PAD_LEFT,PAD_A,PAD_B,PAD_LEFT,PAD_A};
show_title:
    sound_test=0;
    last_dirs=0;
    /* The ending leaves its two animated actors in OAM. Clear both the
     * hardware table and its shadow before replacing the scene with title. */
    vera_oam_init();
    upload_palette(title_screen_palette);
    write_map_rle(title_map_rle,0x20);
    VERA_L0_MAP=0x10;
    title_choice=0;
    if (title_level<1 || title_level>25) title_level=1;
    set_title_prompt(0);
    draw_title_menu();
    /* BRUN may leave a boot key latched in the Apple II keyboard register. */
    KBDSTRB=0;
    keyboard_last_pad=0;
    keyboard_last_held=0;
    keyboard_mute_down=0;
    keyboard_sound_down=0;
    frame_count=0;
    for (;;) {
        wait_frame();
        music_tick();
        sfx_tick();
        ++frame_count;
        if (title_guard) {
            --title_guard;
            if (KEYBOARD&0x80) KBDSTRB=0;
            continue;
        }
        pad=keyboard_pad();
        old_choice=title_choice;
        old_level=title_level;
        dirs=(uint8_t)(pad&(PAD_UP|PAD_DOWN|PAD_LEFT|PAD_RIGHT));
        new_dirs=(uint8_t)(dirs&~last_dirs);
        if (new_dirs&PAD_UP) title_choice=(uint8_t)((title_choice+3)&3);
        if (new_dirs&PAD_DOWN) title_choice=(uint8_t)((title_choice+1)&3);
        if (new_dirs&(PAD_LEFT|PAD_RIGHT)) {
            if (title_choice==1) {
                if ((new_dirs&PAD_LEFT) && title_level>1) --title_level;
                if ((new_dirs&PAD_RIGHT) && title_level<25) ++title_level;
            } else if (title_choice==2) {
                music_muted^=1; music_mute(music_muted);
                title_menu_dirty=1;
            } else if (title_choice==3) {
                sound_muted^=1; sfx_mute(sound_muted);
                title_menu_dirty=1;
            }
        }
        if (old_choice!=title_choice) {
            title_map_palette((uint8_t)(19+old_choice*2),0);
            title_map_palette((uint8_t)(19+title_choice*2),3);
        }
        if (old_level!=title_level) {
            char digits[3];
            digits[0]=(char)('0'+title_level/10);
            digits[1]=(char)('0'+title_level%10);
            digits[2]=0;
            title_map_text(digits,21,21,title_choice==1?3:0);
        }
        if (title_menu_dirty) redraw_title_audio();
        if (new_dirs) {
            if (keyboard_model!=1) keyboard_last_pad=0;
        }
        last_dirs=dirs;
        if (pad) {
            if (pad==code[title_code_index]) {
                if (++title_code_index==6) {
                    title_code_index=0;
                    level_skip=1;
                    sfx_start(1);
                }
            } else title_code_index=0;
        }
        if (pad&PAD_SELECT) current_level=0; /* source cow level */
        if (pad&PAD_START) {
            sound_test=(uint8_t)((pad&(PAD_A|PAD_B))==(PAD_A|PAD_B));
            if (!sound_test && title_choice==2) {
                music_muted^=1; music_mute(music_muted);
                redraw_title_audio();
                continue;
            }
            if (!sound_test && title_choice==3) {
                sound_muted^=1; sfx_mute(sound_muted);
                redraw_title_audio();
                continue;
            }
            if (!sound_test) {
                if (title_choice==1) current_level=title_level;
                else if (current_level!=0) current_level=1;
#ifndef FTM_VERA
                if (!music_muted) music_prefetch(level_music(current_level));
#endif
            }
            break;
        }
    }
    /* NES stops title music and plays SFX_START during its 50-frame start
     * transition. */
    stop_music();
    sfx_start(current_level==0?2:0);
    for (title_guard=0; title_guard<50; ++title_guard) {
        if (!sound_test && title_choice<=1 && !(title_guard&3))
            set_start_option_visible((uint8_t)((title_guard&4)==0));
        wait_frame();
#ifndef FTM_VERA
        music_tick(); /* finish selected-song/SFX preloads during transition */
#endif
        sfx_tick();
    }
    if (sound_test) {
        sound_test_screen();
        play_music(0);
        title_guard=0;
        goto show_title;
    }
    fade_out();
    VERA_L0_MAP=0;
    stop_music();
    if (!load_level_file(current_level)) {
        stop_music();
        for (;;) wait_frame();
    }
    frame_count=0;
    play_music(level_music(current_level));
}

/* The NES title enters this selector when Start+A+B are pressed together.
 * Apple II keyboards do not report simultaneous buttons, so T maps to that
 * chord. K plays the selected sound/song, J stops music, and WASD selects.
 * T or Escape returns to title; Space does not leave this screen. */
static void sound_test_screen(void)
{
    static const uint8_t label[]={
        0,0,0x6C,3, 8,0,0x85,3, 16,0,0x7B,3,
        48,0,0x81,3, 56,0,0x86,3, 64,0,0x8C,3, 128
    };
#ifdef FTM_VERA
    /* Match the PSG test: title, levels 1-5 (Level 2 Alt is native slot 2),
     * game over and ending. Skip the duplicate Level 2 directory entry. */
    static const uint8_t song_map[8]={0,1,2,4,5,6,7,8};
    const uint8_t song_count=8;
#else
    /* Use the original game's Level 2 Alt for BGM 02. */
    static const uint8_t song_map[8]={0,1,3,4,5,6,7,8};
    const uint8_t song_count=8;
#endif
    uint8_t mode=0,effect=0,song=0,pad,key,playing_title=0;
    uint8_t shown_mode=255,shown_effect=255,shown_song=255;
    uint8_t exit_armed=(uint8_t)(keyboard_model!=1);
    pause_last_dirs=0;
    KBDSTRB=0;
    for (;;) {
        wait_frame();
#ifdef FTM_VERA
        if (playing_title) music_tick();
        else music_tick_realtime();
#else
        music_tick();
#endif
        sfx_tick();
        /* Do not let the T key that opened the selector close it again.
         * On a IIe, wait for key release before accepting a new T/Escape. */
        pad=0;
        if (!exit_armed && !(KBDSTRB&0x80)) exit_armed=1;
        if (exit_armed) {
            key=KEYBOARD;
            if (key&0x80) {
                key&=0x7F;
                if (key=='T' || key=='t' || key==0x1B) {
                    KBDSTRB=0;
                    break;
                }
            }
            pad=sound_test_edge(keyboard_pad());
        }
        if (pad&PAD_LEFT) mode=0;
        if (pad&PAD_RIGHT) mode=1;
        if (pad&PAD_UP) {
            if (!mode && effect<14) ++effect;
            else if (mode && (uint8_t)(song+1)<song_count) ++song;
        }
        if (pad&PAD_DOWN) {
            if (!mode && effect) --effect;
            else if (mode && song) --song;
        }
        if (pad&PAD_A) {
            music_stop();
            playing_title=0;
        }
        if (pad&PAD_B) {
            if (mode) {
                music_start(song_map[song]);
                playing_title=(uint8_t)(song==0);
            }
            else sfx_start(effect);
        }
        if (title_menu_dirty) redraw_title_audio();
        /* The labels and digits change only on a selector key press. OAM
         * upload on every tick made music_tick miss VSYNCs in this menu. */
        if (mode!=shown_mode || effect!=shown_effect || song!=shown_song) {
            oam_meta_spr(88,216,3,label);
            oam_spr(116,216,(uint8_t)(0xF0+effect/10),mode?3:1,0);
            oam_spr(124,216,(uint8_t)(0xF0+effect%10),mode?3:1,1);
            oam_spr(164,216,(uint8_t)(0xF0+song),mode?1:3,2);
            vera_oam_present();
            shown_mode=mode;
            shown_effect=effect;
            shown_song=song;
        }
    }
    music_stop();
    vera_oam_init();
}

static uint8_t check_map(uint8_t x,uint8_t y)
{
    uint8_t row;
    if (x>248 || y<48 || y>=208) return TILE_WALL;
    row=(uint8_t)((y-48)>>3);
    return collision_map[(uint16_t)row*32+(x>>3)];
}

static void erase_item(uint8_t x,uint8_t y)
{
    uint16_t address=(uint16_t)(((uint16_t)(y>>3)*64+(x>>3)+4)*2);
    VERA_ADDR_L=(uint8_t)address;
    VERA_ADDR_M=(uint8_t)(address>>8);
    VERA_ADDR_H=0x10;
    VERA_DATA0=0;
    VERA_DATA0=0;
}

/* NES drop_bridge() removes the single bridge tile under the player when a
 * horizontal step begins. The player then loses support and falls normally. */
static void drop_bridge(uint8_t x,uint8_t y)
{
    uint16_t index;
    if (y<48 || y>=208 || x>248) return;
    index=(uint16_t)((y-48)>>3)*32+(x>>3);
    if (collision_map[index]&TILE_BRIDGE) {
        uint8_t slot=particle_next;
        collision_map[index]=0;
        bridge_dropped=1;
        erase_item(x,y);
        particle_x[slot]=x;
        particle_y[slot]=y;
        particle_tile[slot]=0x1B;
        particle_dy[slot]=1;
        particle_frames[slot]=8;
        particle_next=(uint8_t)((slot+1)&3);
        sfx_start(10);
    }
}

static void collect_at(uint8_t x,uint8_t y,uint8_t item_type)
{
    uint16_t index;
    uint8_t i;
    uint8_t type;
    if (y<48 || y>=208 || x>248) return;
    index=(uint16_t)((y-48)>>3)*32+(x>>3);
    type=collision_map[index];
    if (type&item_type) {
        sfx_start(item_type==TILE_ITEM1?3:4);
        for (i=0; i<item_count; ++i) {
            if (item_cell[i]==index) {
                uint8_t slot=particle_next;
                particle_x[slot]=x;
                /* Advance happens at the start of the next frame; offset the
                 * spawn by one step so its first visible position matches NES. */
                particle_y[slot]=y;
                particle_dy[slot]=(uint8_t)-2;
                particle_tile[slot]=(uint8_t)(item_base[i]|
                    (((frame_count>>1)+i)&7));
                particle_frames[slot]=16;
                particle_next=(uint8_t)((slot+1)&3);
                break;
            }
        }
        collision_map[index]=0;
        if (items_left) --items_left;
        erase_item(x,y);
    }
}

static uint8_t collect_current_items(void)
{
    uint8_t before=items_left,x,y;
    collect_at(player_x,player_y,TILE_ITEM1);
    get_alter_position(&x,&y);
    collect_at(x,y,TILE_ITEM2);
    return items_left!=before;
}

static void start_player_move(uint8_t pad)
{
    uint8_t here=check_map(player_x,player_y);
    uint8_t below=check_map(player_x,(uint8_t)(player_y+8));
    if (here&TILE_WATER) return;
    if ((pad&PAD_LEFT) && player_x>=8 &&
        !(check_map((uint8_t)(player_x-8),player_y)&TILE_WALL)) {
        if (below&TILE_BRIDGE) drop_bridge(player_x,(uint8_t)(player_y+8));
        player_move_dir=MOVE_LEFT;
        player_facing_right=0;
    } else if ((pad&PAD_RIGHT) && player_x<=240 &&
        !(check_map((uint8_t)(player_x+8),player_y)&TILE_WALL)) {
        if (below&TILE_BRIDGE) drop_bridge(player_x,(uint8_t)(player_y+8));
        player_move_dir=MOVE_RIGHT;
        player_facing_right=1;
    } else if ((pad&PAD_UP) && (here&TILE_LADDER) && player_y>=56 &&
        (check_map(player_x,(uint8_t)(player_y-8))&TILE_LADDER)) {
        player_move_dir=MOVE_UP;
    } else if ((pad&PAD_DOWN) &&
        ((here|below)&TILE_LADDER) && !(below&(TILE_WALL|TILE_BRIDGE))) {
        player_move_dir=MOVE_DOWN;
    }
    if (player_move_dir) {
        player_move_steps=8;
        player_idle_frames=0;
        if (player_move_dir==MOVE_UP || player_move_dir==MOVE_DOWN)
            player_ladder_pose=1;
        else player_ladder_pose=0;
    }
}

/* NES advances player_x1/player_y1 by one pixel on every frame while the
 * eight-frame tile move is active. Keep that timing rather than teleporting. */
static uint8_t advance_player_move(void)
{
    if (!player_move_steps) return 0;
    switch (player_move_dir) {
        case MOVE_LEFT:
            --player_x;
            player_walk_tile=(uint8_t)(0x94-((player_x>>1)&3)); break;
        case MOVE_RIGHT:
            ++player_x;
            player_walk_tile=(uint8_t)(0x91+((player_x>>1)&3)); break;
        case MOVE_UP:    --player_y; player_ladder_flip=(player_y&4)!=0; break;
        case MOVE_DOWN:  ++player_y; player_ladder_flip=(player_y&4)!=0; break;
    }
    if (!--player_move_steps) player_move_dir=MOVE_NONE;
    return 1;
}

static void get_alter_position(uint8_t *x,uint8_t *y)
{
    if (!sync_type) {
        *x=(uint8_t)(248-player_x);
        if (*x<16) *x=16;
        if (*x>240) *x=240;
        *y=player_y;
    } else {
        *x=player_x;
        *y=(uint8_t)(240-player_y);
        if (*y<48) *y=48;
        if (*y>208) *y=208;
    }
}

/* NES A or B exchanges the two Egos if a charge remains and the other
 * Ego's destination is not a wall. The mirror renderer makes both travel
 * together when the active position moves four pixels each frame. */
static void begin_player_exchange(void)
{
    uint8_t x,y;
    exchange_input_lock=1;
    if (!exchange_left || exchange_active) { sfx_start(9); return; }
    get_alter_position(&x,&y);
    if (check_map(x,y)&TILE_WALL) {
        player_flash_frames=10;
        sfx_start(8); return;
    }
    exchange_x=x;
    exchange_y=y;
    --exchange_left;
    exchange_active=1;
    sfx_start(2);
}

/* NES checks the landing tile before accepting an exchange input. */
static uint8_t check_tile_actions(uint8_t pad)
{
    if (collect_current_items()) return 1;
    if (items_left && (pad&(PAD_A|PAD_B)) && !exchange_input_lock)
        begin_player_exchange();
    return 0;
}

static uint8_t advance_player_exchange(void)
{
    if (!exchange_active) return 0;
    player_flash_frames=2;
    if (player_x<exchange_x) {
        uint8_t d=(uint8_t)(exchange_x-player_x);
        player_x=(uint8_t)(player_x+(d>4?4:d));
    } else if (player_x>exchange_x) {
        uint8_t d=(uint8_t)(player_x-exchange_x);
        player_x=(uint8_t)(player_x-(d>4?4:d));
    }
    if (player_y<exchange_y) {
        uint8_t d=(uint8_t)(exchange_y-player_y);
        player_y=(uint8_t)(player_y+(d>4?4:d));
    } else if (player_y>exchange_y) {
        uint8_t d=(uint8_t)(player_y-exchange_y);
        player_y=(uint8_t)(player_y-(d>4?4:d));
    }
    if (player_x==exchange_x && player_y==exchange_y) {
        exchange_active=0;
        exchange_input_lock=1;
        player_ladder_pose=(uint8_t)((check_map(player_x,player_y)&TILE_LADDER)!=0);
        player_is_falling=0;
        player_walk_tile=0x91;
        player_idle_frames=0;
    }
    return 1;
}

/* Start falling as soon as support is gone, even when no key is pressed.
 * NES game.c moves one pixel per frame for eight frames per tile. */
static uint8_t update_player_fall(void)
{
    uint8_t here,below;
    if (player_fall_steps) {
        player_is_falling=1;
        ++player_y;
        --player_fall_steps;
        return 1;
    }
    here=check_map(player_x,player_y);
    below=check_map(player_x,(uint8_t)(player_y+8));
    if (!(here&TILE_LADDER) && !(below&TILE_FLOOR)) {
        player_is_falling=1;
        player_ladder_pose=0;
        player_idle_frames=49;
        ++player_y;
        player_fall_steps=7;
        return 1;
    }
    player_is_falling=0;
    return 0;
}

static void start_player_death(void)
{
    if (!player_dead) {
        player_dead=1;
        death_frames=50;
        player_move_steps=0;
        player_move_dir=MOVE_NONE;
        player_fall_steps=0;
        exchange_active=0;
        sfx_start(5);
    }
}

static void check_player_hazards(void)
{
    if (player_dead) return;
    if (!exchange_active && !player_move_steps && !player_fall_steps &&
        player_y>=200) start_player_death();
}

static void load_level_entities(void)
{
    uint16_t i;
    items_left=0;
    item_count=0;
    particle_next=0;
    for (i=0; i<4; ++i) {
        particle_x[i]=0;
        particle_y[i]=240;
        particle_tile[i]=0;
        particle_dy[i]=0;
        particle_frames[i]=0;
    }
    for (i=0; i<640; ++i) {
        if (collision_map[i]&(TILE_ITEM1|TILE_ITEM2)) {
            ++items_left;
            if (item_count<ITEM_MAX) {
                uint8_t row=(uint8_t)(i>>5),col=(uint8_t)(i&31);
                item_cell[item_count]=i;
                item_map_offset[item_count]=(uint16_t)(((uint16_t)(row+6)*64+
                                                        col+4)*2);
                item_base[item_count]=(collision_map[i]&TILE_ITEM1)?0xD0:0xD8;
                ++item_count;
            }
        }
    }
    frame_count=0;
    player_move_steps=0;
    player_move_dir=MOVE_NONE;
    player_facing_right=0;
    player_step=0;
    bridge_dropped=0;
    player_fall_steps=0;
    player_ladder_pose=0;
    player_ladder_flip=0;
    player_is_falling=0;
    player_idle_frames=0;
    player_walk_tile=0x90;
    player_flash_frames=0;
    ego_colour_state=0;
    eye_state=255;
    exchange_active=0;
    exchange_input_lock=0;
    player_dead=0;
    death_frames=0;
    level_clear_timer=0;
    level_cleared=0;
    clear_display_timer=0;
    start_delay=50;
    level_fade_frame=0;
    enemy_move_count=8;
}

/* Stream a packed level record from ProDOS. The 640-byte collision array is
 * reused as the disk read buffer until the final collision table is loaded. */
static uint8_t level_read_byte(int fd,uint16_t *remaining,
                               uint16_t *pos,uint16_t *len)
{
    uint8_t value;
    if (!*remaining) return 0;
    if (*pos>=*len) {
        uint16_t want=*remaining>sizeof(collision_map)?sizeof(collision_map):*remaining;
        int n=read(fd,collision_map,want);
        if (n<=0) { *remaining=0; return 0; }
        *pos=0;
        *len=(uint16_t)n;
    }
    value=collision_map[(*pos)++];
    --*remaining;
    return value;
}

static uint8_t load_level_file(uint8_t level)
{
    char filename[5]="LV00";
    uint8_t header[2],params[3],entity_count,i,type,x,y,value,video;
    uint16_t j;
    uint16_t encoded,remaining=0,pos=0,len=0,out=0;
    int fd;
    keyboard_level_reset();
    filename[2]=(char)('0'+level/10);
    filename[3]=(char)('0'+level%10);
    fd=open(filename,O_RDONLY);
    if (fd<0) return 0;
    /* Fade-out has left the old scene black. Keep the new map and its full
     * palette hidden until its initial fade-in level is installed. */
    video=VERA_DC_VID;
    VERA_DC_VID=0x01;
    if (read(fd,header,2)!=2) { close(fd); VERA_DC_VID=video; return 0; }
    encoded=(uint16_t)(header[0]|((uint16_t)header[1]<<8));
    remaining=encoded;
    VERA_ADDR_L=0; VERA_ADDR_M=0; VERA_ADDR_H=0x10;
    while (out<4096 && remaining) {
        uint8_t control=level_read_byte(fd,&remaining,&pos,&len);
        uint8_t count;
        if (control&0x80) {
            count=(uint8_t)((control&0x7F)+3);
            value=level_read_byte(fd,&remaining,&pos,&len);
            while (count-- && out<4096) { VERA_DATA0=value; ++out; }
        } else {
            count=(uint8_t)(control+1);
            while (count-- && out<4096) {
                value=level_read_byte(fd,&remaining,&pos,&len);
                VERA_DATA0=value;
                ++out;
            }
        }
        loading_tick();
    }
    if (out!=4096 || remaining) { close(fd); VERA_DC_VID=video; return 0; }
    if (read(fd,collision_map,512)!=512) { close(fd); VERA_DC_VID=video; return 0; }
    VERA_ADDR_L=0; VERA_ADDR_M=0xFA; VERA_ADDR_H=0x11;
    for (j=0;j<512;j++) VERA_DATA0=collision_map[j];
    for (i=0;i<8;i++) {
        uint8_t k;
        for (k=0;k<8;k++) level_palette[(uint8_t)(i*8+k)]=collision_map[(uint16_t)i*32+k];
    }
    if (read(fd,pause_palette,64)!=64) { close(fd); VERA_DC_VID=video; return 0; }
    if (read(fd,&entity_count,1)!=1) { close(fd); VERA_DC_VID=video; return 0; }
    enemy_count=0;
    for (i=0;i<entity_count;i++) {
        uint8_t entity[3];
        if (read(fd,entity,3)!=3) { close(fd); return 0; }
        type=entity[0]; x=entity[1]; y=entity[2];
        if (type==0x20) {
            player_x=(uint8_t)(x<<3);
            player_y=(uint8_t)(y<<3);
        } else if (enemy_count<ENEMY_MAX) {
            enemy_dir[enemy_count]=type;
            enemy_attr[enemy_count]=(type==ENEMY_LEFT)?0x42:0x02;
            enemy_x[enemy_count]=(uint8_t)(x<<3);
            enemy_y[enemy_count]=(uint8_t)(y<<3);
            ++enemy_count;
        }
    }
    if (read(fd,params,3)!=3 || read(fd,collision_map,640)!=640) {
        close(fd); VERA_DC_VID=video; return 0;
    }
    exchange_left=params[0];
    sync_type=params[1];
    alter_anim_state=params[2];
    close(fd);
    load_level_entities();
    palette_scale(level_palette,1);
    VERA_DC_VID=video;
    return 1;
}

static void restart_level(void)
{
    uint8_t track=level_music(current_level);
    stop_music();
    fade_out();
    if (!load_level_file(current_level)) { game_over=1; return; }
    play_music(track);
    vera_oam_init();
    draw_scene_sprites();
    vera_oam_present();
}

static uint8_t load_raw_asset(const char *name,uint16_t address,uint8_t high,
                              uint16_t size)
{
    int fd=open(name,O_RDONLY);
    uint16_t done=0;
    uint16_t i;
    if (fd<0) return 0;
    VERA_ADDR_L=(uint8_t)address;
    VERA_ADDR_M=(uint8_t)(address>>8);
    VERA_ADDR_H=high;
    while (done<size) {
        uint16_t want=(uint16_t)(size-done);
        int n;
        if (want>sizeof(collision_map)) want=sizeof(collision_map);
        n=read(fd,collision_map,want);
        if (n<=0) { close(fd); return 0; }
        for (i=0;i<(uint16_t)n;i++) VERA_DATA0=collision_map[i];
        done=(uint16_t)(done+n);
        loading_tick();
    }
    close(fd);
    return 1;
}

static void credits_screen(void)
{
    uint8_t frames;
    VERA_DC_VID=0;
    if (!load_raw_asset("CREDITS",0x2000,0x10,4096) ||
        !load_raw_asset("CRPAL",0xFA00,0x11,512)) {
        VERA_DC_VID=0x51;
        return;
    }
    VERA_L0_MAP=0x10;
    VERA_DC_VID=0x51;
    credits_visible=1;
    KBDSTRB=0;
    /* Keep the NES intro's 150-frame hold; Start can skip to the title. */
    for (frames=150; frames; --frames) {
        wait_frame();
        /* Keep static-screen scanout synchronized in the AppleWin VERA fork. */
        if (VERA_DC_VID!=0x51) VERA_DC_VID=0x51;
        if (keyboard_pad()&PAD_START) break;
    }
    credits_visible=0;
    fade_out();
}

static void show_ending(void)
{
    uint8_t confirm=0,y1,y2;
    uint16_t offset;
    stop_music();
    frame_count=0;
    VERA_L0_TIL=0x80;
    if (!load_raw_asset("ENDING",0,0x10,4096) ||
        !load_raw_asset("ENDPAL",0xFA00,0x11,512)) {
        stop_music();
        return;
    }
    play_music(8);
    vera_oam_init();
    for (;;) {
        wait_frame();
        music_tick();
        sfx_tick();
        frame_count=(uint8_t)((frame_count+1)&127);
        offset=(frame_count&16)?252:1020;
        VERA_L0_HSC_L=(uint8_t)offset;
        VERA_L0_HSC_H=(uint8_t)(offset>>8);
        y1=152; y2=152;
        if (frame_count>=50 && frame_count<58) y1=(uint8_t)(201-frame_count);
        else if (frame_count>=58 && frame_count<66) y1=(uint8_t)(87+frame_count);
        if (frame_count>=100 && frame_count<108) y2=(uint8_t)(251-frame_count);
        else if (frame_count>=108 && frame_count<116) y2=(uint8_t)(37+frame_count);
        oam_spr(16,(uint8_t)(y1-8),
                0x90,0x41,60);
        oam_spr(16,y1,
                0xA0,0x41,61);
        oam_spr(232,(uint8_t)(y2-8),
                (uint8_t)(0x97+(frame_count&3)),1,62);
        oam_spr(232,y2,
                (uint8_t)(0xA7+(frame_count&3)),1,63);
        vera_oam_present();
        if (!confirm && (keyboard_pad()&PAD_START)) {
            confirm=20;
            sfx_start(1);
        }
        else if (confirm && !--confirm) break;
    }
    VERA_L0_HSC_L=0; VERA_L0_HSC_H=0;
    stop_music();
    fade_out();
}

static void complete_level(void)
{
    uint8_t track;
    if (current_level>=25 || active_music!=level_music((uint8_t)(current_level+1)))
        stop_music();
    fade_out();
    if (current_level>=25) {
        show_ending();
        lives_remaining=5;
        current_level=1;
        game_over=0;
        play_music(0);
        title_screen();
        return;
    }
    ++current_level;
    if ((current_level==5 || current_level==10 ||
         current_level==15 || current_level==20) && lives_remaining<9)
        ++lives_remaining;
    track=level_music(current_level);
    /* Hold the current song during disk I/O and drawing. Same-theme levels
     * resume at their old position; a new theme starts after the scene. */
    music_pause(1);
    if (!load_level_file(current_level)) { stop_music(); game_over=1; return; }
    vera_oam_init();
    draw_scene_sprites();
    vera_oam_present();
    music_pause(0);
    play_music(track);
}

static void draw_scene_sprites(void)
{
    uint8_t alter_x,alter_y,i,show_player,player_tile,player_attr;
    get_alter_position(&alter_x,&alter_y);
    update_ego_colour();
    show_player=(uint8_t)(!start_delay || (start_delay&8));
    player_attr=player_facing_right?0x41:0x01;
    if (player_is_falling) player_tile=0x96;
    else if (player_ladder_pose) {
        player_tile=0x95; /* ladder pose faces away from the screen */
        player_attr=(uint8_t)(1|(player_ladder_flip?0x40:0));
    } else if (player_move_dir==MOVE_LEFT)
        player_tile=(uint8_t)(0x91+3-((player_x>>1)&3));
    else if (player_move_dir==MOVE_RIGHT)
        player_tile=(uint8_t)(0x91+((player_x>>1)&3));
    else player_tile=player_idle_frames<50?player_walk_tile:0x90;
    /* Active Ego: walk direction chooses both face and NES animation tile. */
    if (show_player) {
        oam_spr(player_x,(uint8_t)(player_y-8),player_tile,player_attr,60);
        oam_spr(player_x,player_y,(uint8_t)(player_tile+0x10),player_attr,61);
        i=(uint8_t)((level_clear_timer||level_cleared)?0:alter_anim_state);
        oam_spr(alter_x,(uint8_t)(alter_y-8),(uint8_t)(0x97+(i&3)),
                (uint8_t)(1|(i&0x40)),62);
        oam_spr(alter_x,alter_y,(uint8_t)(0xA7+(i&3)),
                (uint8_t)(1|(i&0x40)),63);
    } else {
        oam_spr(0,240,0x90,0x41,60);
        oam_spr(0,240,0xA0,0x41,61);
        oam_spr(0,240,0x97,0x01,62);
        oam_spr(0,240,0xA7,0x01,63);
    }
    /* NES sprStats layout: white active Ego, black Alter Ego, and an x
     * marker under each. The two changing digits are updated_stats()'s
     * separate OAM entries at y=23. Keep the original six tile placements. */
    if (!level_cleared) {
        oam_spr(16,15,0x9B,0,52);
        oam_spr(16,23,0xAB,0,53);
        oam_spr(24,23,0xE4,0,54);
        oam_spr(40,15,0x9C,0,55);
        oam_spr(40,23,0xAC,0,56);
        oam_spr(48,23,0xE4,0,57);
        oam_spr(30,23,(uint8_t)(0xE5+lives_remaining),0,58);
        oam_spr(54,23,(uint8_t)(0xE5+exchange_left),0,59);
    } else {
        for (i=52;i<60;i++) oam_spr(0,240,0xFF,0,i);
    }
    if (paused) {
        static const uint8_t resume_text[]={
            0,0,0x6B,0, 8,0,0x84,0, 16,0,0x6C,0,
            24,0,0x6E,0, 32,0,0x8C,0, 40,0,0x84,0, 128
        };
        static const uint8_t restart_text[]={
            0,0,0x6B,0, 8,0,0x84,0, 16,0,0x6C,0,
            24,0,0x6D,0, 32,0,0x80,0, 40,0,0x6B,0,
            48,0,0x6D,0, 128
        };
        static const uint8_t exit_text[]={
            0,0,0x84,0, 8,0,0x7B,0, 16,0,0x88,0, 24,0,0x6D,0,
            40,0,0x86,0, 48,0,0x80,0, 56,0,0x8C,0, 64,0,0x84,0, 128
        };
        uint8_t n;
        for (n=52; n<60; ++n) oam_spr(0,240,0xFF,0,n);
        oam_meta_spr(24,15,40,resume_text);
        if (lives_remaining) oam_meta_spr(24,23,46,restart_text);
        if (lives_remaining) oam_meta_spr(24,31,53,exit_text);
        else oam_meta_spr(24,23,53,exit_text);
        oam_spr(16,(pause_frames&16)?240:(uint8_t)(15+pause_choice*8),0xFF,0,39);
    }
    for (i=0; i<enemy_count; ++i) {
        uint8_t top,lower,attr=enemy_attr[i];
        if (enemy_dir[i]==ENEMY_RIGHT || enemy_dir[i]==ENEMY_LEFT) {
            uint8_t pose=(uint8_t)((frame_count>>2)&3);
            top=(uint8_t)(0xB0+pose); lower=(uint8_t)(0xC0+pose);
        } else {
            uint8_t pose=(uint8_t)((frame_count>>4)&3);
            top=(uint8_t)(0xB4+pose); lower=(uint8_t)(0xC4+pose);
        }
        oam_spr(enemy_x[i],(uint8_t)(enemy_y[i]-8),top,attr,i);
        oam_spr(enemy_x[i],enemy_y[i],lower,attr,(uint8_t)(ENEMY_MAX+i));
    }
    for (i=0; i<4; ++i) {
        if (particle_frames[i])
            oam_spr(particle_x[i],particle_y[i],particle_tile[i],3,
                    (uint8_t)(16+i));
        else
            oam_spr(0,240,particle_tile[i],3,(uint8_t)(16+i));
    }
}

static void hide_pause_sprites(void)
{
    uint8_t i;
    for (i=39;i<61;i++) oam_spr(0,240,0xFF,0,i);
}

static void leave_game_to_title(void)
{
    paused=0;
    music_pause(0);
    set_level_palette(0);
    fade_out();
    stop_music();
    lives_remaining=5;
    game_over=0;
    gameover_music_started=0;
    current_level=1;
    play_music(0);
    vera_oam_init();
    title_screen();
    draw_scene_sprites();
    vera_oam_present();
}

static void set_level_palette(uint8_t dim)
{
    const uint8_t *p=dim?pause_palette:level_palette;
    uint8_t bank,i;
    for (bank=0;bank<8;bank++) {
        VERA_ADDR_L=(uint8_t)(bank*32);
        VERA_ADDR_M=0xFA; VERA_ADDR_H=0x11;
        for (i=0;i<8;i++) VERA_DATA0=*p++;
    }
    if (!dim) { eye_state=255; ego_colour_state=0; }
}

static void update_ego_colour(void)
{
    static const uint8_t colours[6]={0xAF,4,0x93,13,0,5};
    const uint8_t *p;
    uint8_t state=0,i;
    if (paused) return;
    if (player_dead) state=((50-death_frames)&4)?3:2;
    else if (player_flash_frames) {
        if (--player_flash_frames) state=(frame_count&1)?1:2;
    }
    if (state==ego_colour_state) return;
    ego_colour_state=state;
    VERA_ADDR_L=0xA2; VERA_ADDR_M=0xFA; VERA_ADDR_H=0x11;
    if (!state) {
        p=level_palette+42;
        for (i=0;i<6;i++) VERA_DATA0=*p++;
    } else {
        p=colours+(state-1)*2;
        for (i=0;i<3;i++) { VERA_DATA0=p[0]; VERA_DATA0=p[1]; }
    }
}

static void update_enemy_eyes(void)
{
    static const uint8_t colours[6]={0,5,0x20,12,0x86,15};
    uint8_t state=(uint8_t)((frame_count>>4)&3);
    if (frame_count&1) return;
    if (state==3) state=1;
    if (state==eye_state) return;
    eye_state=state;
    VERA_ADDR_L=0xC2; VERA_ADDR_M=0xFA; VERA_ADDR_H=0x11;
    VERA_DATA0=colours[state*2]; VERA_DATA0=colours[state*2+1];
}

static void loading_tick(void)
{
    uint8_t vsync,lo,mid,hi;
    if (active_music==255) return;
    vsync=(uint8_t)(VERA_ISR&0x01);
    if (vsync) {
        lo=VERA_ADDR_L; mid=VERA_ADDR_M; hi=VERA_ADDR_H;
        music_tick(); sfx_tick();
        VERA_ADDR_L=lo; VERA_ADDR_M=mid; VERA_ADDR_H=hi;
        VERA_ISR=0x01;
    }
}

static void palette_scale(const uint8_t *p,uint8_t scale)
{
    uint8_t bank,i,gb,r;
    for (bank=0;bank<8;bank++) {
        VERA_ADDR_L=(uint8_t)(bank*32);
        VERA_ADDR_M=0xFA; VERA_ADDR_H=0x11;
        for (i=0;i<4;i++) {
            gb=*p++; r=*p++;
            VERA_DATA0=(uint8_t)(((((gb>>4)*scale)>>2)<<4)|(((gb&15)*scale)>>2));
            VERA_DATA0=(uint8_t)((r*scale)>>2);
        }
    }
}

static void fade_out(void)
{
    uint8_t bank,i,frame;
    for (bank=0;bank<8;bank++) {
        VERA_ADDR_L=(uint8_t)(bank*32);
        VERA_ADDR_M=0xFA; VERA_ADDR_H=0x11;
        for (i=0;i<8;i++) fade_palette[(uint8_t)(bank*8+i)]=VERA_DATA0;
    }
    for (frame=0;frame<16;frame++) {
        wait_frame(); music_tick(); sfx_tick();
        if (!(frame&3)) palette_scale(fade_palette,(uint8_t)(3-(frame>>2)));
    }
}

/* NES game.c advances enemies one pixel every other frame. Every eight
 * advances it checks the next tile edge/landing and reverses at the boundary. */
static void advance_enemies(void)
{
    uint8_t i;
    if (player_dead || level_clear_timer || level_cleared) return;
    /* The NES freezes both actors and enemies for the entire exchange. */
    if (exchange_active) return;
    if (frame_count&1) return;
    if (!exchange_active) {
        uint8_t right=(uint8_t)(player_x+8),bottom=(uint8_t)(player_y+8);
        for (i=0; i<enemy_count; ++i) {
            if (enemy_y[i]>=player_y && enemy_y[i]<bottom &&
                enemy_x[i]>=player_x && enemy_x[i]<right) {
                start_player_death();
            }
        }
    }
    for (i=0; i<enemy_count; ++i) {
        switch (enemy_dir[i]) {
            case ENEMY_LEFT:  --enemy_x[i]; break;
            case ENEMY_RIGHT: ++enemy_x[i]; break;
            case ENEMY_UP:    --enemy_y[i]; break;
            case ENEMY_DOWN:  ++enemy_y[i]; break;
        }
    }
    if (--enemy_move_count) return;
    for (i=0; i<enemy_count; ++i) {
        uint8_t x=enemy_x[i],y=enemy_y[i];
        switch (enemy_dir[i]) {
            case ENEMY_LEFT:
                if (x<8 || !(check_map((uint8_t)(x-8),(uint8_t)(y+8))&TILE_FLOOR) ||
                    (check_map((uint8_t)(x-8),y)&TILE_WALL)) {
                    enemy_dir[i]=ENEMY_RIGHT; enemy_attr[i]=0x02;
                }
                break;
            case ENEMY_RIGHT:
                if (x>240 || !(check_map((uint8_t)(x+8),(uint8_t)(y+8))&TILE_FLOOR) ||
                    (check_map((uint8_t)(x+8),y)&TILE_WALL)) {
                    enemy_dir[i]=ENEMY_LEFT; enemy_attr[i]=0x42;
                }
                break;
            case ENEMY_UP:
                if (y<56 || (check_map(x,(uint8_t)(y-8))&
                    (TILE_WALL|TILE_BRIDGE|TILE_WATER))) enemy_dir[i]=ENEMY_DOWN;
                break;
            case ENEMY_DOWN:
                if (check_map(x,(uint8_t)(y+8))&
                    (TILE_WALL|TILE_BRIDGE|TILE_WATER)) enemy_dir[i]=ENEMY_UP;
                break;
        }
    }
    enemy_move_count=8;
}

static uint8_t keyboard_pad(void)
{
    uint8_t pad=0,held,joy=joystick_pad();
    uint8_t ch=KEYBOARD;
    /* $C010 bit 7 is the IIe any-key-down flag. On II+ it is floating bus. */
    if (!keyboard_model)
        keyboard_model=(*(volatile uint8_t*)0xFBB3==0x06)?1:2;
    if (!(ch&0x80)) {
        if (keyboard_model!=1) {
            /* II+ has no key-up flag; a cleared strobe arms the next press. */
            keyboard_mute_down=0;
            keyboard_sound_down=0;
            return joy|(keyboard_last_pad&(PAD_UP|PAD_DOWN|PAD_LEFT|PAD_RIGHT));
        }
        held=(uint8_t)(KBDSTRB&0x80); /* enhanced IIe any-key-down flag */
        if (!held) {
            keyboard_last_held=0;
            keyboard_mute_down=0;
            keyboard_sound_down=0;
        }
        return joy|(held?(uint8_t)(keyboard_last_pad&(PAD_A|PAD_B|PAD_UP|PAD_DOWN|PAD_LEFT|PAD_RIGHT)):0);
    }
    ch &= 0x7F;
    held=keyboard_model==1?(uint8_t)(KBDSTRB&0x80):0;
    if (keyboard_model!=1) KBDSTRB=0; /* acknowledge II+ key latch */
    switch (ch) {
        case 0x0B: case 'W': case 'w': pad=PAD_UP; break;
        case 0x0A: case 'S': case 's': pad=PAD_DOWN; break;
        case 0x08: case 'A': case 'a': pad=PAD_LEFT; break;
        case 0x15: case 'D': case 'd': pad=PAD_RIGHT; break;
        case 'J': case 'j': pad=PAD_A; break;
        case 'K': case 'k': pad=PAD_B; break;
        case ' ': pad=PAD_START; break;
        case 'T': case 't': pad=PAD_START|PAD_A|PAD_B; break;
        case '1': pad=PAD_SELECT; break;
        case 'G': case 'g': joystick_init(); break;
        case 'M': case 'm':
            if (!keyboard_mute_down) {
                music_muted^=1;
                music_mute(music_muted);
                title_menu_dirty=1;
                keyboard_mute_down=1;
            }
            break;
        case 'N': case 'n':
            if (!keyboard_sound_down) {
                sound_muted^=1;
                sfx_mute(sound_muted);
                title_menu_dirty=1;
                keyboard_sound_down=1;
            }
            break;
    }
    ch=(uint8_t)(held && keyboard_last_held && pad==keyboard_last_pad &&
                !(pad&(PAD_A|PAD_B|PAD_UP|PAD_DOWN|PAD_LEFT|PAD_RIGHT)));
    if (keyboard_model==1 || (pad&(PAD_UP|PAD_DOWN|PAD_LEFT|PAD_RIGHT)))
        keyboard_last_pad=pad;
    else
        keyboard_last_pad=0;
    keyboard_last_held=held;
    return joy|(ch?0:pad);
}

/* A II+ key latch survives level transitions unless $C010 is accessed. Clear
 * it for the new level while keeping the II+ game's last direction active
 * until another key is pressed. IIe reads its true held-key flag instead. */
static void keyboard_level_reset(void)
{
    KBDSTRB=0;
    keyboard_last_pad=0;
    keyboard_last_held=0;
    keyboard_mute_down=0;
    keyboard_sound_down=0;
}

void main(void)
{
    uint8_t pad,falling,was_falling,collected,logic_delta,logic_step;
#ifdef FTM_VERA
    static uint8_t ftm_rate_phase;
#endif
    vera_oam_init();
    VERA_DC_VID=0x51; /* VGA + Layer 0 + VERA hardware sprites */
    vera_sync_init();
    /* File I/O uses fixed buffers in iobuf.s, outside program and C stack. */
    music_init();
    joystick_init();
    if (!load_raw_asset("TILES",0,0x11,16384)) {
        for (;;) wait_frame();
    }
    credits_screen();
    play_music(0);
    title_screen();
    draw_scene_sprites();
    vera_oam_present();

    for (;;) {
        wait_frame();
        music_tick();
        pad=keyboard_pad();
        if (game_over && !gameover_music_started) {
            stop_music();
            VERA_L0_TIL=0x80;
            load_raw_asset("GOVER",0,0x10,4096);
            load_raw_asset("GOPAL",0xFA00,0x11,512);
            play_music(7);
            vera_oam_init();
            gameover_timer=500;
            gameover_music_started=1;
        }
        if (game_over) {
            if ((pad&PAD_START) || (gameover_timer && !--gameover_timer)) {
                stop_music(); fade_out();
                lives_remaining=5;
                game_over=0;
                paused=0;
                gameover_music_started=0;
                current_level=1;
                play_music(0);
                title_screen();
                draw_scene_sprites();
                vera_oam_present();
            }
            vera_oam_present();
            continue;
        }
        if (paused) {
            uint8_t dirs=(uint8_t)(pad&(PAD_UP|PAD_DOWN));
            uint8_t new_dirs=(uint8_t)(dirs&~pause_last_dirs);
            uint8_t redraw=0;
            pause_last_dirs=dirs;
            sfx_tick();
            if (pad&PAD_START) {
                if (pause_choice==2 || (pause_choice==1 && !lives_remaining)) {
                    leave_game_to_title();
                    continue;
                }
                paused=0;
                redraw=1;
                sfx_start(0);
                if (pause_choice==1 && lives_remaining) {
                    --lives_remaining;
                    restart_level();
                } else {
                    music_pause(0);
                    set_level_palette(0);
                    hide_pause_sprites();
                }
            }
            else if (!pause_move_cooldown && (new_dirs&PAD_UP) && pause_choice) {
                --pause_choice; pause_frames=0; pause_move_cooldown=10; sfx_start(1);
                redraw=1;
                if (keyboard_model!=1) keyboard_last_pad=0;
            }
            else if (!pause_move_cooldown && (new_dirs&PAD_DOWN) &&
                     pause_choice<(lives_remaining?2:1)) {
                ++pause_choice; pause_frames=0; pause_move_cooldown=10; sfx_start(1);
                redraw=1;
                if (keyboard_model!=1) keyboard_last_pad=0;
            }
            if (pause_move_cooldown) --pause_move_cooldown;
            ++pause_frames;
            if ((pause_frames&15)==0) redraw=1; /* cursor blink edge */
            if (!game_over && redraw) {
                draw_scene_sprites();
                vera_oam_present();
            }
            continue;
        }
        /* The live FTM player leaves about 40 game iterations per second.
         * Alternate one and two NES-time steps to keep gameplay near 60 Hz. */
#ifdef FTM_VERA
        logic_delta=(uint8_t)((++ftm_rate_phase&1)?2:1);
#else
        logic_delta=1;
#endif
        for (logic_step=0;logic_step<logic_delta;logic_step++) sfx_tick();
        if (level_fade_frame<16) {
            for (logic_step=0;logic_step<logic_delta && level_fade_frame<16;logic_step++) {
                if (!(level_fade_frame&3)) palette_scale(level_palette,(uint8_t)(1+(level_fade_frame>>2)));
                ++level_fade_frame;
            }
        }
        if (!player_dead && !level_cleared)
            for (logic_step=0;logic_step<logic_delta;logic_step++) advance_item_particles();
        if (!player_dead && !level_cleared) {
            for (logic_step=0;logic_step<logic_delta;logic_step++)
                alter_anim_state=(uint8_t)((alter_anim_state<<1)^((alter_anim_state&0x80)?0xCF:0));
            animate_background();
            animate_items();
        }
        if (start_delay) {
            start_delay=(uint8_t)(start_delay>logic_delta?start_delay-logic_delta:0);
            draw_scene_sprites();
            vera_oam_present();
            continue;
        }
        if ((pad&PAD_SELECT) && level_skip) {
            level_clear_timer=24;
            prefetch_next_level_music();
            continue;
        }
        if ((pad&PAD_START) && !player_dead &&
            !level_clear_timer && !level_cleared) {
            paused=1;
            pause_choice=0;
            pause_frames=0;
            pause_last_dirs=0;
            pause_move_cooldown=0;
            music_pause(1);
            set_level_palette(1);
            sfx_start(0);
            sfx_tick(); /* start the pause cue before the menu repaint */
            draw_scene_sprites();
            vera_oam_present();
            continue;
        }
        if (!(pad&(PAD_A|PAD_B))) exchange_input_lock=0;
        if (player_dead) {
            if (death_frames)
                death_frames=(uint8_t)(death_frames>logic_delta?death_frames-logic_delta:0);
            if (!death_frames && !game_over) {
                /* NES's restart counter underflows only when a death occurs
                 * after the displayed reserve has already reached zero. */
                if (lives_remaining) {
                    --lives_remaining;
                    restart_level();
                    continue;
                } else game_over=1;
            }
            draw_scene_sprites();
            vera_oam_present();
            continue;
        }
        if (level_cleared) {
            if (clear_display_timer) {
                for (logic_step=0;logic_step<logic_delta && clear_display_timer;logic_step++) {
                    --clear_display_timer;
                    if ((clear_display_timer&15)==7) draw_level_clear(0);
                    if ((clear_display_timer&15)==15) draw_level_clear(1);
                }
                if (!clear_display_timer) {
                    complete_level();
                    continue;
                }
            }
            draw_scene_sprites();
            vera_oam_present();
            continue;
        }
        if (level_clear_timer) {
            level_clear_timer=(uint8_t)(level_clear_timer>logic_delta?level_clear_timer-logic_delta:0);
            if (!level_clear_timer) {
                level_cleared=1;
                clear_display_timer=126;
                draw_level_clear(1);
                sfx_start(14);
            }
            draw_scene_sprites();
            vera_oam_present();
            continue;
        }
        if (exchange_active) {
            for (logic_step=0;logic_step<logic_delta;logic_step++) advance_player_exchange();
            falling=0;
        } else if (player_move_steps) {
            for (logic_step=0;logic_step<logic_delta;logic_step++) advance_player_move();
            falling=0;
        } else {
            /* A two-step FTM update can finish a fall after this frame's
             * pickup check was skipped. Wait until the next update checks
             * the landing tile before accepting lateral movement. */
            collected=(uint8_t)(player_fall_steps!=0);
            if (!player_fall_steps) {
                if (check_tile_actions(pad)) { collected=1; pad=0; }
                if (items_left && !exchange_active &&
                    (check_map(player_x,player_y)&TILE_WATER)) {
                    start_player_death();
                    draw_scene_sprites();
                    vera_oam_present();
                    continue;
                }
            }
            was_falling=player_is_falling;
            falling=(exchange_active || !items_left)?0:update_player_fall();
            if (falling && logic_delta==2) {
                /* The first source tick can finish an eight-pixel fall.
                 * NES checks items and exchange before the next gravity tick. */
                if (!player_fall_steps) {
                    if (check_tile_actions(pad)) { collected=1; pad=0; }
                }
                falling=(items_left && !exchange_active)?update_player_fall():0;
            }
            if (!items_left) {
                level_clear_timer=24;
                prefetch_next_level_music();
                draw_scene_sprites();
                vera_oam_present();
                continue;
            }
            if (falling && !was_falling) sfx_start(6);
            else if (!falling && was_falling && !exchange_active) sfx_start(7);
            if (pad && !falling && !collected && !exchange_active) {
                {
                    uint8_t old_dir=player_move_dir;
                    start_player_move(pad);
                    if (player_move_steps && !old_dir) {
                        if (player_ladder_pose) sfx_start(13);
                        else if (!bridge_dropped) {
                            sfx_start(player_step?12:11);
                            player_step^=1;
                        }
                        bridge_dropped=0;
                        for (logic_step=0;logic_step<logic_delta;logic_step++) advance_player_move();
                    }
                }
            }
            if (!falling && !exchange_active && !player_move_steps && player_idle_frames<50)
                player_idle_frames=(uint8_t)(player_idle_frames+logic_delta>50?50:player_idle_frames+logic_delta);
        }
        check_player_hazards();
        for (logic_step=0;logic_step<logic_delta;logic_step++) {
            ++frame_count;
            advance_enemies();
        }
        if (!player_dead && !exchange_active) update_enemy_eyes();
        draw_scene_sprites();
        vera_oam_present();
    }
}
