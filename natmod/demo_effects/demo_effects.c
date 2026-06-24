#include "py/dynruntime.h"
#include "pv_types.h"
#include "effects.h"

#define FRAMEWIDTH 240
#define FRAMEHEIGHT 320
#define HALFHEIGHT (FRAMEHEIGHT/2)

uint16_t* palette = NULL;
mp_obj_t* display_obj = NULL;

// Avoid data race between cores by having separate seeds
uint32_t seed[2];
// Can't pull in anything from stdlib so just implement something from https://en.wikipedia.org/wiki/Xorshift
uint32_t rand(uint32_t* seed)
{
    uint32_t x = *seed;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *seed = x;
    return x;
}

static mp_obj_t set_display(mp_obj_t new_display_obj)
{
    mp_buffer_info_t tmp;
    mp_get_buffer_raise(new_display_obj, &tmp, MP_BUFFER_READ);
    if (tmp.typecode != 'H')
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Display framebuffer must be of type uint16 (H)"));
    }
    if (tmp.len != FRAMEWIDTH * FRAMEHEIGHT * sizeof(uint16_t))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Display framebuffer unexpected size"));
    }
    display_obj = new_display_obj;

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(set_display_obj, set_display);

static mp_obj_t set_palette(mp_obj_t pal_obj)
{
    mp_buffer_info_t tmp;
    mp_get_buffer_raise(pal_obj, &tmp, MP_BUFFER_READ);
    if (tmp.typecode != 'H')
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Palette must be of type uint16 (H)"));
    }
    if (tmp.len != 256 * sizeof(uint16_t))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Palette must have 256 entries"));
    }
    palette = (uint16_t*)tmp.buf;

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(set_palette_obj, set_palette);

mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args)
{
    MP_DYNRUNTIME_INIT_ENTRY

    seed[0] = 0x7273E7B6; // just four bytes from /dev/random
    seed[1] = 0xEC0F8626; // just four bytes from /dev/random

    init_pv_types();
    mp_store_global(MP_QSTR_set_display, MP_OBJ_FROM_PTR(&set_display_obj));
    mp_store_global(MP_QSTR_set_palette, MP_OBJ_FROM_PTR(&set_palette_obj));


    MP_DYNRUNTIME_INIT_EXIT
}
