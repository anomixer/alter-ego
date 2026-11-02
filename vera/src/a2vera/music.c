/* VERA-VRAM-cached PSG player for the Apple II game loop.
 * ProDOS reads happen only when a track/effect bank is loaded. Playback reads
 * events from VERA VRAM, so the 60 Hz tick never waits for a file read. */
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include "music.h"

#ifndef VERA_BASE
#define VERA_BASE 0xC200
#endif
#define VERA_ADDR_L (*(volatile uint8_t*)(VERA_BASE+0x00))
#define VERA_ADDR_M (*(volatile uint8_t*)(VERA_BASE+0x01))
#define VERA_ADDR_H (*(volatile uint8_t*)(VERA_BASE+0x02))
#define VERA_DATA0  (*(volatile uint8_t*)(VERA_BASE+0x03))
#define PSG_BASE_LO 0xC0
#define PSG_BASE_MI 0xF9

/* $0000-$3FFF holds the live nametables. Tile pages occupy $10000-$13FFF,
 * palette/PSG/OAM are at the top of VRAM. Keep cached audio in free $4000+.
 * The largest current song is 17,096 bytes; reserve 20 KB for future tracks. */
#define MUSIC_VRAM_BASE 0x04000u
#define MUSIC_VRAM_ALT 0x09000u
#define MUSIC_VRAM_CAPACITY 0x05000u
#define MUSIC_READ_SIZE 256
#define SFX_VRAM_BASE 0x0E000u
#define SFX_BANK_SIZE (15u*384u)
#define SFX_SLOT_SIZE 384u
#define MUSIC_EVENT_MAX 18

static const char *const song_paths[10]={
    "TITLE.PSG","LEVEL1.PSG","LEVEL2.PSG","LEVEL2ALT.PSG",
    "LEVEL3.PSG","LEVEL4.PSG","LEVEL5.PSG","GAMEOVER.PSG",
    "CONGRATS.PSG","CLEAR.PSG"
};
/* Also used as the ProDOS staging buffer while loading, then for one event. */
static uint8_t music_buffer[MUSIC_READ_SIZE],music_registers[16];
static uint16_t sfx_pos,sfx_end,sfx_cache_length;
static uint16_t music_pos,music_length;
static uint8_t music_active,music_paused,music_muted,sfx_active,sfx_muted;
static uint8_t sfx_cache_loaded;
static uint8_t event_data[MUSIC_EVENT_MAX*2];
static uint16_t music_base,prefetch_base,prefetch_length;
static int prefetch_fd=-1;
static uint8_t prefetch_song,prefetch_ready,music_song=255,requested_song=255;
static int sfx_cache_fd=-1;
void __fastcall__ music_start_impl(uint8_t song);

static void set_vram_address(uint16_t address)
{
    VERA_ADDR_L=(uint8_t)address;
    VERA_ADDR_M=(uint8_t)(address>>8);
    VERA_ADDR_H=0x10; /* All cached tracks/effects fit below VRAM $10000. */
}

static void psg_silence(void)
{
    uint8_t i;
    VERA_ADDR_L=PSG_BASE_LO;
    VERA_ADDR_M=PSG_BASE_MI;
    VERA_ADDR_H=0x11;
    for (i=0; i<64; ++i) VERA_DATA0=0;
    for (i=0;i<16;i++) music_registers[i]=0;
}

static uint16_t load_file_to_vram(const char *name,uint16_t base,
                                  uint16_t limit)
{
    int fd,n;
    uint16_t total=0;
    fd=open(name,O_RDONLY);
    if (fd<0) return 0;
    while ((n=read(fd,music_buffer,sizeof(music_buffer)))>0) {
        uint16_t i;
        if ((uint16_t)n>(uint16_t)(limit-total)) {
            total=0;
            break;
        }
        set_vram_address((uint16_t)(base+total));
        for (i=0;i<(uint16_t)n;i++) VERA_DATA0=music_buffer[i];
        total=(uint16_t)(total+(uint16_t)n);
    }
    close(fd);
    if (n<0) return 0;
    return total;
}

static uint8_t stream_byte(uint8_t *value)
{
    if (music_pos>=music_length) return 0;
    *value=VERA_DATA0;
    ++music_pos;
    return 1;
}

static void sfx_silence(void)
{
    VERA_ADDR_L=0xD2; VERA_ADDR_M=PSG_BASE_MI; VERA_ADDR_H=0x11;
    VERA_DATA0=0;
    VERA_ADDR_L=0xD6;
    VERA_DATA0=0;
}

/* Load the small fixed-slot effect bank to unused VERA VRAM incrementally
 * while the title screen runs. Once gameplay starts, effect playback is VRAM
 * only and never opens or reads a ProDOS file. */
static void sfx_cache_tick(void)
{
    int n;
    uint16_t i;
    if(sfx_cache_loaded) return;
    if(sfx_cache_fd<0){
        sfx_cache_fd=open("SFXBANK",O_RDONLY);
        if(sfx_cache_fd<0) return;
    }
    n=read(sfx_cache_fd,music_buffer,sizeof(music_buffer));
    if(n<=0){
        close(sfx_cache_fd); sfx_cache_fd=-1;
        if(n==0 && sfx_cache_length==SFX_BANK_SIZE) sfx_cache_loaded=1;
        else sfx_cache_length=0;
        return;
    }
    if((uint16_t)n>(uint16_t)(SFX_BANK_SIZE-sfx_cache_length)){
        close(sfx_cache_fd); sfx_cache_fd=-1; sfx_cache_length=0;
        return;
    }
    set_vram_address((uint16_t)(SFX_VRAM_BASE+sfx_cache_length));
    for(i=0;i<(uint16_t)n;i++) VERA_DATA0=music_buffer[i];
    sfx_cache_length=(uint16_t)(sfx_cache_length+(uint16_t)n);
}

static void sfx_stop_impl(void)
{
    sfx_active=0;
    sfx_pos=sfx_end=0;
    sfx_silence();
}

void music_stop_impl(void)
{
    sfx_stop_impl();
    music_active=0;
    music_pos=0;
    requested_song=255;
    psg_silence();
    music_paused=0;
}

void __fastcall__ sfx_start_impl(uint8_t effect)
{
    if (sfx_muted || effect>=15 || !sfx_cache_loaded) return;
    sfx_stop_impl();
    sfx_pos=(uint16_t)((uint16_t)effect*SFX_SLOT_SIZE);
    sfx_end=(uint16_t)(sfx_pos+SFX_SLOT_SIZE);
    sfx_active=1;
}

void sfx_tick_impl(void)
{
    uint8_t frame[4],i;
    if (sfx_muted || !sfx_active) return;
    if ((uint16_t)(sfx_pos+4)>sfx_end) {
        sfx_stop_impl(); return;
    }
    set_vram_address((uint16_t)(SFX_VRAM_BASE+sfx_pos));
    for(i=0;i<4;i++) frame[i]=VERA_DATA0;
    if(frame[3]==0xFF){sfx_stop_impl();return;}
    VERA_ADDR_L=0xD0; VERA_ADDR_M=PSG_BASE_MI; VERA_ADDR_H=0x11;
    for (i=0;i<4;i++) VERA_DATA0=frame[i];
    VERA_ADDR_L=0xD4;
    for (i=0;i<4;i++) VERA_DATA0=frame[i];
    sfx_pos=(uint16_t)(sfx_pos+4);
}

void __fastcall__ sfx_mute_impl(uint8_t mute)
{
    sfx_muted=(uint8_t)(mute!=0);
    if (sfx_muted) sfx_stop_impl();
}

void music_init_impl(void)
{
    music_pos=music_length=0;
    music_song=255;
    requested_song=255;
    music_active=music_paused=music_muted=0;
    sfx_active=0;
    sfx_muted=0;
    sfx_cache_fd=-1;
    sfx_pos=sfx_end=sfx_cache_length=0;
    sfx_cache_loaded=0;
    music_base=MUSIC_VRAM_BASE;
    prefetch_base=MUSIC_VRAM_ALT;
    prefetch_length=0;
    prefetch_fd=-1;
    prefetch_ready=0;
    psg_silence();
}

void __fastcall__ music_prefetch_impl(uint8_t song)
{
    if (music_muted || song>=10) return;
    if (prefetch_fd>=0) close(prefetch_fd);
    prefetch_fd=-1;
    prefetch_ready=0;
    prefetch_length=0;
    prefetch_song=song;
    prefetch_base=(music_base==MUSIC_VRAM_BASE)?MUSIC_VRAM_ALT:MUSIC_VRAM_BASE;
    prefetch_fd=open(song_paths[song],O_RDONLY);
}

static void prefetch_tick(void)
{
    int n;
    uint16_t i;
    if (prefetch_fd<0 || prefetch_ready) return;
    n=read(prefetch_fd,music_buffer,sizeof(music_buffer));
    if (n<=0) {
        close(prefetch_fd);
        prefetch_fd=-1;
        if (n==0 && prefetch_length) prefetch_ready=1;
        return;
    }
    if ((uint16_t)n>(uint16_t)(MUSIC_VRAM_CAPACITY-prefetch_length)) {
        close(prefetch_fd);
        prefetch_fd=-1;
        prefetch_length=0;
        return;
    }
    set_vram_address((uint16_t)(prefetch_base+prefetch_length));
    for (i=0;i<(uint16_t)n;i++) VERA_DATA0=music_buffer[i];
    prefetch_length=(uint16_t)(prefetch_length+(uint16_t)n);
}

void __fastcall__ music_pause_impl(uint8_t pause)
{
    uint8_t i,value;
    if (music_paused==pause) return;
    music_paused=pause;
    if (!music_active) {
        if (!pause && !music_muted && requested_song<10) {
            /* Resume deferred loading if the user unmuted while paused. */
            music_start_impl(requested_song);
        }
        return;
    }
    for (i=2;i<16;i+=4) {
        value=(pause || music_muted)?0:music_registers[i];
        VERA_ADDR_L=(uint8_t)(PSG_BASE_LO+i);
        VERA_ADDR_M=PSG_BASE_MI; VERA_ADDR_H=0x11;
        VERA_DATA0=value;
    }
    if (!pause)
        for (i=0;i<16;i++) if ((i&3)!=2) {
            VERA_ADDR_L=(uint8_t)(PSG_BASE_LO+i);
            VERA_ADDR_M=PSG_BASE_MI; VERA_ADDR_H=0x11;
            VERA_DATA0=music_registers[i];
        }
}

void __fastcall__ music_mute_impl(uint8_t mute)
{
    uint8_t i;
    music_muted=(uint8_t)(mute!=0);
    if (music_muted) {
        if (prefetch_fd>=0) { close(prefetch_fd); prefetch_fd=-1; }
        prefetch_ready=0;
    }
    if (music_paused) return;
    if (music_active) {
        for (i=2;i<16;i+=4) {
            VERA_ADDR_L=(uint8_t)(PSG_BASE_LO+i);
            VERA_ADDR_M=PSG_BASE_MI; VERA_ADDR_H=0x11;
            VERA_DATA0=music_muted?0:music_registers[i];
        }
    } else if (!music_muted && requested_song<10) {
        music_start_impl(requested_song);
    }
}

static void music_load_requested(uint8_t song)
{
    uint16_t length;
    if (music_song==song && music_length) {
        music_pos=0;
        music_active=1;
        return;
    }
    prefetch_tick();
    if (prefetch_ready && prefetch_song==song) {
        length=prefetch_length;
        music_base=prefetch_base;
        prefetch_ready=0;
    } else {
        if (prefetch_fd>=0) { close(prefetch_fd); prefetch_fd=-1; }
        music_song=255;
        music_length=0;
        length=load_file_to_vram(song_paths[song],MUSIC_VRAM_BASE,
                                 MUSIC_VRAM_CAPACITY);
        music_base=MUSIC_VRAM_BASE;
    }
    if (!length) return;
    music_length=length;
    music_pos=0;
    music_song=song;
    music_active=1;
}

void __fastcall__ music_start_impl(uint8_t song)
{
    music_stop_impl();
    if (song>=10) return;
    requested_song=song;
    if (!music_muted) music_load_requested(song);
}

static void music_fail(void)
{
    music_stop_impl();
}

void music_tick_impl(void)
{
    uint8_t count,reg,value,loop_lo,loop_hi,i;
    sfx_cache_tick();
    prefetch_tick();
    if (!music_active || music_paused) return;
    if (music_pos>=music_length) { music_fail(); return; }
    set_vram_address((uint16_t)(music_base+music_pos));
    if (!stream_byte(&count)) { music_fail(); return; }
    if (count==0xFF) {
        /* Converter-produced game tracks loop at frame zero. */
        if (!stream_byte(&loop_lo) || !stream_byte(&loop_hi)) {
            music_fail(); return;
        }
        music_pos=0;
        return;
    }
    if (count>MUSIC_EVENT_MAX) { music_fail(); return; }
    for (i=0;i<(uint8_t)(count*2);i++)
        if (!stream_byte(&event_data[i])) { music_fail(); return; }
    for (i=0;i<count;i++) {
        reg=event_data[(uint8_t)(i*2)];
        value=event_data[(uint8_t)(i*2+1)];
        if (reg>=64) { music_fail(); return; }
        if (reg<16) music_registers[reg]=value;
        VERA_ADDR_L=(uint8_t)(PSG_BASE_LO+reg);
        VERA_ADDR_M=PSG_BASE_MI;
        VERA_ADDR_H=0x11;
        VERA_DATA0=(uint8_t)((music_muted && (reg&3)==2)?0:value);
    }
}
