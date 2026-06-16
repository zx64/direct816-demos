#include "py/dynruntime.h"
#include "pv_rect.h"

#define FRAMEWIDTH 240
#define FRAMEHEIGHT 320
#define HALFHEIGHT (FRAMEHEIGHT/2)


#define TEST_RECT  // Requries LINK_RUNTIME
#if defined(TEST_RECT)
static mp_obj_t test_rect(mp_obj_t rect_obj)
{
    pv_rect r = get_rect(rect_obj);
    const float area = r.w * r.h;
    mp_printf(MP_PYTHON_PRINTER, "r: %.2f, %.2f [%.2f x %.2f] area: %.2f\n", r.x, r.y, r.w, r.h, area);
    return mp_obj_new_float(area);
}
static MP_DEFINE_CONST_FUN_OBJ_1(test_rect_obj, test_rect);
#endif


uint16_t* palette = NULL;
mp_obj_t* display_obj = NULL;
uint32_t* x_scroll = NULL;
uint32_t* y_scroll = NULL;
uint16_t angle_len = 0, angle_mask = 0;

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
    //mp_printf(MP_PYTHON_PRINTER, "buf info: len %u typecode %c\n", tmp.len, tmp.typecode);
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

static mp_obj_t set_scroll_arrays(mp_obj_t x_scroll_obj, mp_obj_t y_scroll_obj)
{
    mp_buffer_info_t tmp_x, tmp_y;
    mp_get_buffer_raise(x_scroll_obj, &tmp_x, MP_BUFFER_READ);
    if (tmp_x.typecode != 'I')
    {
        mp_raise_ValueError(MP_ERROR_TEXT("X scroll array must be of type uint32 (I)"));
    }
    if (tmp_x.len == 0)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Scroll arrays can't be empty"));
    }

    mp_get_buffer_raise(y_scroll_obj, &tmp_y, MP_BUFFER_READ);
    if (tmp_y.typecode != 'I')
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Y scroll array must be of type uint32 (I)"));
    }
    if (tmp_x.len != tmp_y.len)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("X and Y scroll arrays must have same length"));
    }

    uint32_t num_entries = tmp_x.len / sizeof(uint32_t);
    if (num_entries > 0xFFFF)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Scroll arrays are bigger than 65535"));
    }

    if ((num_entries & (num_entries - 1)) != 0)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Scroll array lengths must be power of two"));
    }

    //mp_printf(MP_PYTHON_PRINTER, "Using new scroll arrays %p %p len %u mask %X", tmp_x.buf, tmp_y.buf, num_entries, num_entries - 1);
    angle_len = num_entries;
    angle_mask = num_entries - 1;
    x_scroll = (uint32_t*)tmp_x.buf;
    y_scroll = (uint32_t*)tmp_y.buf;

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(set_scroll_arrays_obj, set_scroll_arrays);


static mp_obj_t palcycle(mp_obj_t tick_obj, mp_obj_t y_start_obj)
{
    if (!palette)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Palette is not set"));
    }
    if (!display_obj)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Display is not set"));
    }

    mp_buffer_info_t tmp;
    mp_get_buffer_raise(display_obj, &tmp, MP_BUFFER_RW);
    uint16_t* fb = (uint16_t*)tmp.buf;

    uint16_t tick = mp_obj_get_int(tick_obj) & 0xFFFF;
    uint16_t y_start = mp_obj_get_int(y_start_obj) & 0xFFFF;
    if (!((y_start == 0) || (y_start == HALFHEIGHT)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid y_start value"));
    }

    fb += y_start * FRAMEWIDTH;

    uint16_t val16 = palette[tick & 0xFF];
    uint32_t val = val16 << 16 | val16;
    uint32_t count = FRAMEWIDTH * HALFHEIGHT / 2;
    uint32_t* fb32 = (uint32_t*)fb;
    while (count--)
    {
        *fb32++ = val;
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(palcycle_obj, palcycle);

static mp_obj_t simplexor(mp_obj_t tick_obj, mp_obj_t y_start_obj)
{
    if (!palette)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Palette is not set"));
    }
    if (!display_obj)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Display is not set"));
    }

    mp_buffer_info_t tmp;
    mp_get_buffer_raise(display_obj, &tmp, MP_BUFFER_RW);
    uint16_t* fb = (uint16_t*)tmp.buf;

    uint16_t tick = mp_obj_get_int(tick_obj) & 0xFFFF;
    uint16_t y_start = mp_obj_get_int(y_start_obj) & 0xFFFF;
    if (!((y_start == 0) || (y_start == HALFHEIGHT)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid y_start value"));
    }

    fb += y_start * FRAMEWIDTH;

    for (uint16_t y = y_start; y < (y_start + HALFHEIGHT); ++y)
    {
        for (uint16_t x = 0; x < FRAMEWIDTH; ++x)
        {
            uint8_t c = (uint8_t)((x ^ y) + tick);
            //mp_printf(MP_PYTHON_PRINTER, "%u,%u = %u [%X]\n", x, y, c, palette[c]);
            *fb++ = palette[c];
        }
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(simplexor_obj, simplexor);

static mp_obj_t xor_scroll(mp_obj_t tick_obj, mp_obj_t y_start_obj)
{
    if (!palette)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Palette is not set"));
    }
    if (!display_obj)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Display is not set"));
    }
    if (!x_scroll || !y_scroll)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Scroll arrays are not set"));
    }

    mp_buffer_info_t tmp;
    mp_get_buffer_raise(display_obj, &tmp, MP_BUFFER_RW);
    uint16_t* fb = (uint16_t*)tmp.buf;

    uint16_t tick = mp_obj_get_int(tick_obj) & 0xFFFF;
    uint16_t y_start = mp_obj_get_int(y_start_obj) & 0xFFFF;
    if (!((y_start == 0) || (y_start == HALFHEIGHT)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid y_start value"));
    }

    fb += y_start * FRAMEWIDTH;

    uint32_t x_shift = x_scroll[tick & angle_mask],
             y_shift = y_scroll[tick & angle_mask];
    for (uint16_t y = y_start; y < (y_start + HALFHEIGHT); ++y)
    {
        for (uint16_t x = 0; x < FRAMEWIDTH; ++x)
        {
            uint8_t c = (uint8_t)(((x+x_shift) ^ (y+y_shift)) + tick);
            *fb++ = palette[c];
        }
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(xor_scroll_obj, xor_scroll);

static mp_obj_t plasma_scroll(mp_obj_t tick_obj, mp_obj_t y_start_obj)
{
    if (!palette)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Palette is not set"));
    }
    if (!display_obj)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Display is not set"));
    }
    if (!x_scroll || !y_scroll)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Scroll arrays are not set"));
    }

    mp_buffer_info_t tmp;
    mp_get_buffer_raise(display_obj, &tmp, MP_BUFFER_RW);
    uint16_t* fb = (uint16_t*)tmp.buf;

    uint32_t tick = mp_obj_get_int(tick_obj);
    const uint16_t y_start = mp_obj_get_int(y_start_obj) & 0xFFFF;
    if (!((y_start == 0) || (y_start == HALFHEIGHT)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid y_start value"));
    }

    fb += y_start * FRAMEWIDTH;

    uint32_t tick_fast = tick << 2;
    uint32_t global_y_shift = y_scroll[tick & angle_mask];
    for (uint16_t y = y_start; y < (y_start + HALFHEIGHT); ++y)
    {
        uint32_t line_y_shift = y_scroll[(global_y_shift + y) & angle_mask] + tick_fast;
        for (uint16_t x = 0; x < FRAMEWIDTH; ++x)
        {
            uint32_t c = line_y_shift + x_scroll[(tick + x) & angle_mask];
            *fb++ = palette[c & 0xFF];
        }
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(plasma_scroll_obj, plasma_scroll);

static mp_obj_t random_noise(mp_obj_t tick_obj, mp_obj_t y_start_obj)
{
    (void)tick_obj;
    if (!display_obj)
    {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Display is not set"));
    }

    mp_buffer_info_t tmp;
    mp_get_buffer_raise(display_obj, &tmp, MP_BUFFER_RW);
    uint16_t* fb = (uint16_t*)tmp.buf;

    const uint16_t y_start = mp_obj_get_int(y_start_obj) & 0xFFFF;
    if (!((y_start == 0) || (y_start == HALFHEIGHT)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid y_start value"));
    }

    uint32_t* local_seed = &seed[0];

    if (y_start)
    {
        local_seed = &seed[1];
        fb += y_start * FRAMEWIDTH;
    }

    uint32_t count = HALFHEIGHT * FRAMEWIDTH;
    while (count--)
    {
        *fb++ = rand(local_seed) & 0xFFFF;
    }

    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(random_noise_obj, random_noise);

mp_obj_t mpy_init(mp_obj_fun_bc_t *self, size_t n_args, size_t n_kw, mp_obj_t *args)
{
    MP_DYNRUNTIME_INIT_ENTRY

    seed[0] = 0x7273E7B6; // just four bytes from /dev/random
    seed[1] = 0xEC0F8626; // just four bytes from /dev/random

    init_rect_type();
#if defined(TEST_RECT)
    mp_store_global(MP_QSTR_test_rect, MP_OBJ_FROM_PTR(&test_rect_obj));
#endif

    mp_store_global(MP_QSTR_set_display, MP_OBJ_FROM_PTR(&set_display_obj));
    mp_store_global(MP_QSTR_set_palette, MP_OBJ_FROM_PTR(&set_palette_obj));
    mp_store_global(MP_QSTR_set_scroll_arrays, MP_OBJ_FROM_PTR(&set_scroll_arrays_obj));
    mp_store_global(MP_QSTR_palcycle, MP_OBJ_FROM_PTR(&palcycle_obj));
    mp_store_global(MP_QSTR_simplexor, MP_OBJ_FROM_PTR(&simplexor_obj));
    mp_store_global(MP_QSTR_xor_scroll, MP_OBJ_FROM_PTR(&xor_scroll_obj));
    mp_store_global(MP_QSTR_plasma_scroll, MP_OBJ_FROM_PTR(&plasma_scroll_obj));
    mp_store_global(MP_QSTR_random_noise, MP_OBJ_FROM_PTR(&random_noise_obj));


    MP_DYNRUNTIME_INIT_EXIT
}
