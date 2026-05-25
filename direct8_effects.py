import micropython
from common_effects import load_palette
from array import array


WIDTH = const(240)
HEIGHT = const(320)
HALF_HEIGHT = const(HEIGHT // 2)
SIZE = const(WIDTH * HEIGHT)
HALF_SIZE = const(SIZE // 2)
# These values are for performing 32-bit pointer arithmetic on an 8-bit pointer
# Unlike C, Viper pointer arithmetic always operates in bytes rather than sizeof(*p)
SIZE_BYTES = const(SIZE)
HALF_SIZE_BYTES = const(SIZE_BYTES // 2)


def use_palette(filename, layer=-1):
    temp = load_palette(filename)
    display.direct8_palette(temp, layer)
    return temp


@micropython.viper
def fill8(c: uint):
    fb32 = ptr32(display)
    c = c & 0xFF
    v32 = c << 24 | c << 16 | c << 8 | c
    end: uint = uint(fb32) + SIZE_BYTES
    while uint(fb32) != end:
        fb32[0] = v32
        fb32 = ptr32(uint(fb32) + 4)


@micropython.viper
def fill8_both_layers(c: uint):
    fb32 = ptr32(display)
    c = c & 0xFF
    v32 = c << 24 | c << 16 | c << 8 | c
    end: uint = uint(fb32) + SIZE_BYTES * 2
    while uint(fb32) != end:
        fb32[0] = v32
        fb32 = ptr32(uint(fb32) + 4)


@micropython.viper
def fill8_upper(c: uint):
    fb32 = ptr32(uint(ptr32(display)) + SIZE_BYTES)
    c = c & 0xFF
    v32 = c << 24 | c << 16 | c << 8 | c
    end: uint = uint(fb32) + SIZE_BYTES
    while uint(fb32) != end:
        fb32[0] = v32
        fb32 = ptr32(uint(fb32) + 4)


@micropython.viper
def palcycle(t: uint, y_min: uint):
    fb32 = ptr32(display)

    if y_min != uint(0):
        fb32 = ptr32(uint(fb32) + HALF_SIZE_BYTES)

    c = t & 0xFF
    v32 = c << 24 | c << 16 | c << 8 | c

    end: uint = uint(fb32) + HALF_SIZE_BYTES
    while uint(fb32) != end:
        fb32[0] = v32
        fb32 = ptr32(uint(fb32) + 4)


@micropython.viper
def simple_xor(t: uint, y_min: uint):
    fb = ptr8(display)

    if y_min == uint(0):
        idx = uint(0)
    else:
        idx = uint(HALF_SIZE)

    for y in range(y_min, y_min + HALF_HEIGHT):
        for x in range(WIDTH):
            c = ((x ^ y) + t) & 0xFF
            fb[idx] = c
            idx += 1


# Picking these makes the checker scroll line up nicely with the simple_xor background
SKIP_X = const(64)
SKIP_X2 = const(48)


@micropython.viper
def layer1_checker_scroll(t: uint, y_min: uint):
    _direct8_effects.xor_scroll(t, y_min)
    fb = ptr8(display)

    if y_min == uint(0):
        idx = uint(SIZE)
    else:
        idx = uint(SIZE + HALF_SIZE)

    val = t & 0xFF
    if val == uint(0):
        val = uint(1)
    for y in range(y_min, y_min + HALF_HEIGHT):
        y1bit = uint(((y + t) >> 4) & 1)
        idx += uint(SKIP_X)
        for x in range(SKIP_X, WIDTH - SKIP_X2):
            xbit = ((x - t) >> 4 & 1) ^ y1bit
            if xbit:
                fb[idx] = val
            else:
                fb[idx] = 0
            idx += 1
        idx += uint(SKIP_X2)
