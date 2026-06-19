#include "py/dynruntime.h"
#include "pv_types.h"

const mp_obj_type_t* type_rect = NULL;

void init_rect_type()
{
    type_rect = (const mp_obj_type_t*)mp_load_global(MP_QSTR_rect);
}
