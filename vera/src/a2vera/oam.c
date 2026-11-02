/* NES metasprites retain their original 8x8 tile placements. The assembly
 * adapter owns the OAM shadow and only uploads entries that changed. */
#include <stdint.h>
extern uint8_t __fastcall__ oam_spr(uint8_t x,uint8_t y,uint8_t tile,
                                  uint8_t attr,uint8_t id);

uint8_t __fastcall__ oam_meta_spr(uint8_t x,uint8_t y,uint8_t id,
                                const uint8_t *data)
{
    while (data[0]!=0x80 && id<64) {
        oam_spr((uint8_t)(x+data[0]),(uint8_t)(y+data[1]),
                data[2],data[3],id++);
        data+=4;
    }
    return id;
}
