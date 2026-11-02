/*
 * FamiTone stream interpreter with a native VERA PSG backend.
 *
 * It consumes the original FamiTone v1.24 song modules assembled from the
 * checked-in music_*.s data. It does not call the Mockingboard AY player.
 */
#include <stdint.h>
#include "ftm_tables.h"

#ifndef VERA_BASE
#define VERA_BASE 0xC200u
#endif
#define VERA_ADDR_L (*(volatile uint8_t*)(VERA_BASE+0x00))
#define VERA_ADDR_M (*(volatile uint8_t*)(VERA_BASE+0x01))
#define VERA_ADDR_H (*(volatile uint8_t*)(VERA_BASE+0x02))
#define VERA_DATA0  (*(volatile uint8_t*)(VERA_BASE+0x03))

typedef struct {
    const uint8_t *data;
    uint8_t pos;
    uint8_t repeat;
    int8_t value;
} FtmEnvelope;

typedef struct {
    const uint8_t *stream;
    const uint8_t *return_stream;
    uint8_t note;
    uint8_t instrument;
    uint8_t repeat;
    uint8_t ref_rows;
    uint8_t duty;
} FtmChannel;

#define FAMI_MODULE_DIRECTORY ((const uint8_t*)0x6750u)
static const uint8_t volume_curve[16] = {
     0,15,20,24,29,33,37,41,46,50,54,58,63,63,63,63
};
/* VERA compares phase[16:10] (0..127) against a 6-bit pulse width. Its
 * maximum high duty is therefore 50%. These values approximate NES 12.5%,
 * 25%, and 50%; NES 75% is a phase-inverted 25% pulse. */
static const uint8_t duty_curve[4] = {0x0F,0x1F,0x3F,0x1F};
/* VERA phase words for NES APU noise period indices 0..15. The fastest NES
 * periods exceed VERA's frequency ceiling, so those entries clamp at 65535. */

static FtmChannel channels[4];
FtmEnvelope envelopes[11];
extern void ftm_step_envelopes(void);
static const uint8_t *instrument_data;
static uint8_t song_speed, row_countdown, active, paused, muted;
static uint8_t tick_mode, tick_fraction;

static uint16_t read_word(const uint8_t *p)
{
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static void silence_music(void)
{
    uint8_t i;
    VERA_ADDR_L=0xC0; VERA_ADDR_M=0xF9; VERA_ADDR_H=0x11;
    for (i=0;i<16;i++) VERA_DATA0=(i&3)==2?0:0;
}

static void load_instrument(uint8_t channel)
{
    FtmChannel *ch=&channels[channel];
    const uint8_t *ins=instrument_data+((uint16_t)ch->instrument<<3);
    uint8_t base=(channel==3)?9:(uint8_t)(channel*3);
    uint8_t count=(channel==3)?2:3;
    uint8_t i;
    /* FamiTone instrument layout: volume, note offset, pitch offset, duty. */
    if (channel==3) {
        /* FamiTone allocates only two noise envelopes: the first instrument
         * pointer is its volume envelope; it does not apply pulse pitch or
         * arpeggio to the NES noise timer. */
        envelopes[base].data=(const uint8_t*)read_word(ins+0);
        envelopes[base+1].data=(const uint8_t*)read_word(ins+2);
    } else {
        envelopes[base].data=(const uint8_t*)read_word(ins+0);
        envelopes[base+1].data=(const uint8_t*)read_word(ins+2);
        envelopes[base+2].data=(const uint8_t*)read_word(ins+4);
    }
    for (i=0;i<count;i++) {
        envelopes[base+i].pos=0;
        envelopes[base+i].repeat=0;
        envelopes[base+i].value=0;
    }
    ch->duty=ins[6];
}

static uint8_t step_channel(uint8_t index)
{
    FtmChannel *ch=&channels[index];
    uint8_t b,guard=0,resume=0;
    if (ch->ref_rows) {
        --ch->ref_rows;
        if (!ch->ref_rows) {
            ch->stream=ch->return_stream;
            resume=1;
        }
    }
    /* FamiTone jumps back to the return stream as soon as a reference block
     * ends; it deliberately bypasses the channel's previous repeat counter. */
    if (!resume && ch->repeat) { --ch->repeat; return 0; }
    while (++guard) {
        b=*ch->stream++;
        if (b<0x40) {
            ch->note=b;
            load_instrument(index);
            return 1;
        }
        if (b<0x80) { ch->instrument=(uint8_t)(b&0x3F); continue; }
        if (b<0xC0) { ch->repeat=(uint8_t)(b&0x3F); return 0; }
        if (b==0xFE) { ch->stream=(const uint8_t*)read_word(ch->stream); continue; }
        if (b==0xFF) {
            ch->ref_rows=*ch->stream++;
            ch->return_stream=ch->stream+2;
            ch->stream=(const uint8_t*)read_word(ch->stream);
            continue;
        }
        song_speed=(uint8_t)(b&0x3F);
        if (!song_speed) song_speed=1;
        if (guard==0xFF) break;
    }
    return 0;
}

static void step_row(void)
{
    uint8_t i;
    for (i=0;i<4;i++) step_channel(i);
}

static uint8_t env_volume(uint8_t channel)
{
    uint8_t idx=(channel==3)?9:(uint8_t)(channel*3);
    return (uint8_t)envelopes[idx].value&0x0F;
}

static uint16_t channel_phase(uint8_t channel)
{
    FtmChannel *ch=&channels[channel];
    int16_t note=ch->note;
    int16_t period;
    uint8_t base=(channel==3)?9:(uint8_t)(channel*3);
    if (note==63) return 0;
    if (channel==3) {
        /* FamiTone adds the noise instrument's second envelope, then
         * complements the low nibble into the NES APU's period index. */
        note+=envelopes[base+1].value;
        note=(int16_t)(0x0F-(note&0x0F));
        return FTM_NOISE_PHASE_TABLE[(uint8_t)note];
    }
    note+=envelopes[base+1].value;
    if (note<0) note=0;
    if (note>59) return 0;
    period=(int16_t)ftm_note_period[(uint8_t)note];
    period+=envelopes[base+2].value;
    if (period<1) period=1;
    if (period>FTM_FREQ_TABLE_LIMIT) period=FTM_FREQ_TABLE_LIMIT;
    /* NES triangle clocks its waveform at half the pulse frequency for the
     * same timer period (CPU / 32 versus CPU / 16). */
    if (channel==2) return FTM_PHASE_TABLE[(uint16_t)period]>>1;
    return FTM_PHASE_TABLE[(uint16_t)period];
}

static void render_music(void)
{
    uint8_t out[16],i;
    VERA_ADDR_L=0xC0; VERA_ADDR_M=0xF9; VERA_ADDR_H=0x11;
    for (i=0;i<4;i++) {
        uint16_t phase=channel_phase(i);
        uint8_t level=(active&&!paused&&!muted&&phase)?volume_curve[env_volume(i)]:0;
        /* Map the NES envelope through VERA's nonlinear gain curve and apply
         * the same 2x music gain used by the approved .PSG converter. */
        uint8_t volume=level;
        uint8_t wave;
        if (i<2) wave=duty_curve[(channels[i].duty>>6)&3];
        else if (i==2) wave=0x80;
        else wave=0xC0;
        out[i*4+0]=(uint8_t)phase;
        /* VERA PSG frequency is a full 16-bit phase increment. */
        out[i*4+1]=(uint8_t)(phase>>8);
        out[i*4+2]=volume?(uint8_t)(0xC0|volume):0;
        out[i*4+3]=wave;
    }
    for (i=0;i<16;i++) VERA_DATA0=out[i];
}

/* Public C hooks. The production overlay will wrap these at $1000. */
void __fastcall__ ftm_player_start(const uint8_t *module)
{
    uint8_t i;
    const uint8_t *p=module;
    for (i=0;i<4;i++) {
        channels[i].stream=(const uint8_t*)read_word(p+i*2);
        channels[i].return_stream=0;
        channels[i].note=63;
        channels[i].instrument=0;
        channels[i].repeat=channels[i].ref_rows=0;
        channels[i].duty=0x30;
    }
    instrument_data=(const uint8_t*)read_word(module+10);
    song_speed=module[12]?module[12]:1;
    row_countdown=0;
    active=1;
    for (i=0;i<4;i++) load_instrument(i);
    render_music();
}

void ftm_player_tick(void)
{
    if (!active) return;
    if (!paused) {
        if (!row_countdown) {
            step_row();
            row_countdown=(uint8_t)(song_speed-1);
        } else --row_countdown;
        ftm_step_envelopes();
    }
}

void __fastcall__ ftm_player_pause(uint8_t pause)
{
    paused=(uint8_t)(pause!=0);
    render_music();
}

void __fastcall__ ftm_player_mute(uint8_t mute)
{
    muted=(uint8_t)(mute!=0);
    render_music();
}

void ftm_player_stop(void)
{
    active=0;
    paused=0;
    silence_music();
}

void __fastcall__ music_start_impl(uint8_t song)
{
    const uint8_t *module;
    if (song<10) {
        tick_mode=(uint8_t)(song==0?0:(song<=6?1:2));
        tick_fraction=0;
        module=(const uint8_t*)read_word(FAMI_MODULE_DIRECTORY+((uint16_t)song<<1));
        ftm_player_start(module);
    }
}

/* The optimized envelope engine gives about 40 game iterations/second.
 * Alternate one/two source ticks for level music. Title and sound-test BGM 00
 * run once per VSYNC with the original seven-tick FamiTone row speed. */
void music_tick_impl(void)
{
    if (!active || paused) return;
    ftm_player_tick();
    if (tick_mode==1 && (++tick_fraction&1)) {
        ftm_player_tick();
    }
    render_music();
}
/* Sound test runs at VSYNC rate, so it needs exactly one source tick. */
void music_tick_realtime_impl(void)
{
    if (!active || paused) return;
    ftm_player_tick();
    render_music();
}
void __fastcall__ music_pause_impl(uint8_t pause) { ftm_player_pause(pause); }
void __fastcall__ music_mute_impl(uint8_t mute) { ftm_player_mute(mute); }
void music_stop_impl(void) { ftm_player_stop(); }
void music_init_impl(void) { active=paused=muted=tick_mode=tick_fraction=0; silence_music(); }
void __fastcall__ music_prefetch_impl(uint8_t song) { (void)song; }
