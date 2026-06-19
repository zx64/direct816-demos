#include "py/dynruntime.h"
#include "pv_types.h"

const mp_obj_type_t* type_rect = NULL;
const mp_obj_type_t* type_vec2 = NULL;

void init_pv_types()
{
    type_rect = (const mp_obj_type_t*)mp_load_global(MP_QSTR_rect);
    type_vec2 = (const mp_obj_type_t*)mp_load_global(MP_QSTR_vec2);
}
