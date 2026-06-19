#pragma once

void init_pv_types(); // must call this in module entry point

typedef struct
{
    float x, y, w, h;
} pv_rect;

typedef struct
{
    mp_obj_base_t base;
    pv_rect value;
} pv_rect_obj;

extern const mp_obj_type_t* type_rect;

static inline pv_rect get_rect(mp_obj_t* rect_obj)
{
    const mp_obj_type_t* t = mp_obj_get_type(rect_obj);
    if (t != type_rect)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected rect"));
    }

    pv_rect_obj* wrapper = (pv_rect_obj*)MP_OBJ_TO_PTR(rect_obj);
    return wrapper->value;
}

typedef struct
{
    float x, y;
} pv_vec2;

typedef struct
{
    mp_obj_base_t base;
    pv_vec2 value;
} pv_vec2_obj;

extern const mp_obj_type_t* type_vec2;

static inline pv_vec2 get_vec2(mp_obj_t* vec2_obj)
{
    const mp_obj_type_t* t = mp_obj_get_type(vec2_obj);
    if (t != type_vec2)
    {
        mp_raise_TypeError(MP_ERROR_TEXT("expected vec2"));
    }

    pv_vec2_obj* wrapper = (pv_vec2_obj*)MP_OBJ_TO_PTR(vec2_obj);
    return wrapper->value;
}
