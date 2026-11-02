/* Existing VERA SFXBANK reader, kept separate from the new FTM music engine. */
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include "music.h"

#ifndef VERA_BASE
#define VERA_BASE 0xC200u
#endif
#define VERA_ADDR_L (*(volatile uint8_t*)(VERA_BASE+0x00))
#define VERA_ADDR_M (*(volatile uint8_t*)(VERA_BASE+0x01))
#define VERA_ADDR_H (*(volatile uint8_t*)(VERA_BASE+0x02))
#define VERA_DATA0  (*(volatile uint8_t*)(VERA_BASE+0x03))
#define PSG_BASE_MI 0xF9
#define SFX_READ_SIZE 32

static uint8_t buffer[SFX_READ_SIZE],pos,length,active,muted;
static char effect_path[6]="SFX00";
static int fd=-1;

static void silence(void)
{
    VERA_ADDR_L=0xD2; VERA_ADDR_M=PSG_BASE_MI; VERA_ADDR_H=0x11;
    VERA_DATA0=0;
    VERA_ADDR_L=0xD6;
    VERA_DATA0=0;
}

static void stop(void)
{
    active=0;
    if (fd>=0) close(fd);
    fd=-1;
    pos=length=0;
    silence();
}

void __fastcall__ sfx_start_impl(uint8_t effect)
{
    if (muted || effect>=15) return;
    stop();
    effect_path[3]=(char)('0'+effect/10);
    effect_path[4]=(char)('0'+effect%10);
    fd=open(effect_path,O_RDONLY);
    if (fd>=0) active=1;
}

void sfx_tick_impl(void)
{
    int n;
    uint8_t i;
    if (muted || !active) return;
    if (pos>=length) {
        n=read(fd,buffer,sizeof(buffer));
        if (n<=0) { stop(); return; }
        pos=0; length=(uint8_t)n;
    }
    if ((uint16_t)(pos+4)>length || buffer[pos+3]==0xFF) { stop(); return; }
    VERA_ADDR_L=0xD0; VERA_ADDR_M=PSG_BASE_MI; VERA_ADDR_H=0x11;
    for (i=0;i<4;i++) VERA_DATA0=buffer[pos+i];
    VERA_ADDR_L=0xD4;
    for (i=0;i<4;i++) VERA_DATA0=buffer[pos+i];
    pos=(uint8_t)(pos+4);
}

void __fastcall__ sfx_mute_impl(uint8_t mute)
{
    muted=(uint8_t)(mute!=0);
    if (muted) stop();
}

