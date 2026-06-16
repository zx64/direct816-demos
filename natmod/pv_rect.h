#pragma once

extern const mp_obj_type_t* type_rect;
void init_rect_type(); // must call this in module entry point

typedef struct
{
    float x, y, w, h;
} pv_rect;

typedef struct
{
    mp_obj_base_t base;
    pv_rect r;
} pv_rect_obj;


static inline pv_rect get_rect(mp_obj_t* rect_obj)
{
    const mp_obj_type_t* t = mp_obj_get_type(rect_obj);
    if (t != type_rect)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected rect"));
    }

    pv_rect_obj* ro = (pv_rect_obj*)MP_OBJ_TO_PTR(rect_obj);
    return ro->r;
}
