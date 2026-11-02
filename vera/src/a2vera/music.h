#ifndef AE2VERA_MUSIC_H
#define AE2VERA_MUSIC_H

void music_init(void);
void __fastcall__ music_start(unsigned char song);
void music_tick(void);
#ifdef FTM_VERA
void music_tick_realtime(void);
#endif
void __fastcall__ music_prefetch(unsigned char song);
void music_stop(void);
void __fastcall__ music_pause(unsigned char pause);
void __fastcall__ music_mute(unsigned char mute);
void __fastcall__ sfx_start(unsigned char effect);
void __fastcall__ sfx_mute(unsigned char mute);
void sfx_tick(void);

#endif
