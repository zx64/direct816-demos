import math
import micropython
from array import array

WIDTH = const(240)
HEIGHT = const(320)
HALF_HEIGHT = const(HEIGHT // 2)
SIZE = const(WIDTH * HEIGHT)
HALF_SIZE = const(SIZE // 2)
QUARTER_SIZE = const(SIZE // 4)

angle_bits = const(10)
angle_len = const(1 << angle_bits)
angle_mask = const(angle_len - 1)
orbit_radius = const(800)


def mapped_angle(angle):
    return math.radians(360.0 * angle / angle_mask)


x_scroll = array(
    "I",
    [
        math.floor(math.sin(mapped_angle(theta)) * orbit_radius)
        for theta in range(angle_len)
    ],
)

y_scroll = array(
    "I",
    [
        math.floor(math.cos(mapped_angle(2.0 * theta)) * orbit_radius)
        for theta in range(angle_len)
    ],
)


@micropython.viper
def fill_565(v: uint):
    v16: uint = v & 0xFFFF
    v32: uint = v16 << 16 | v16
    fb32 = ptr32(display)
    for idx in range(HALF_SIZE):
        fb32[idx] = v32


@micropython.viper
def byteswap16(v: uint) -> uint:
    a = (v & 0xFF00) >> 8
    b = (v & 0x00FF) << 8
    return b | a


@micropython.viper
def bgr565(r: uint, g: uint, b: uint) -> uint:
    v = ((r & 0b11111000) << 8 | (g & 0b11111100) << 3 | b >> 3) & 0xFFFF
    return v
    # a = (v & 0xFF00) >> 8
    # b = (v & 0x00FF) << 8
    # return b | a


if 1:
    palette = array(
        "H",
        [bgr565(i, i // 4, i // 8) for i in range(0, 256, 2)]
        + [bgr565(i, i // 4, i // 8) for i in range(255, 0, -2)],
    )
else:
    palette = array("H", [bgr565(i, i // 4, i // 8) for i in range(256)])
palmask = const(255)
assert len(palette) == (palmask + 1)


@micropython.viper
def palcycle(t: uint, y_min: uint):
    fb32 = ptr32(display)
    pal = ptr16(palette)

    if y_min == uint(0):
        base = uint(0)
    else:
        base = uint(QUARTER_SIZE)

    val16: uint = pal[t & palmask]
    val = val16 << 16 | val16
    for idx in range(base, base + QUARTER_SIZE):
        fb32[idx] = val


@micropython.viper
def simple_xor(t: uint, y_min: uint):
    fb16 = ptr16(display)
    pal = ptr16(palette)

    if y_min == uint(0):
        idx = uint(0)
    else:
        idx = uint(HALF_SIZE)
    for y in range(y_min, y_min + HALF_HEIGHT):
        for x in range(WIDTH):
            c = (x ^ y) + t
            fb16[idx] = pal[c & palmask]
            idx += 1


@micropython.viper
def xor_scroll(t: uint, y_min: uint):
    fb16 = ptr16(display)
    pal = ptr16(palette)
    x_shift = ptr32(x_scroll)[t & angle_mask]
    y_shift = ptr32(y_scroll)[t & angle_mask]

    if y_min == uint(0):
        idx = uint(0)
    else:
        idx = uint(HALF_SIZE)
    for y in range(y_min, y_min + HALF_HEIGHT):
        for x in range(WIDTH):
            c = ((x + x_shift) ^ (y + y_shift)) + t
            fb16[idx] = pal[c & palmask]
            idx += 1


@micropython.viper
def plasma_scroll(t: uint, y_min: uint):
    fb16 = ptr16(display)
    pal = ptr16(palette)

    x_shift = ptr32(x_scroll)
    y_shift = ptr32(y_scroll)

    if y_min == uint(0):
        idx = uint(0)
    else:
        idx = uint(HALF_SIZE)
    ts = t << 2
    ta = y_shift[t & angle_mask]
    for y in range(y_min, y_min + HALF_HEIGHT):
        ys = y_shift[(ta + y) & angle_mask] + ts
        for x in range(WIDTH):
            c = ys + x_shift[(t + x) & angle_mask]
            fb16[idx] = pal[c & palmask]
            idx += 1


box_x = array("H", [0xFFFF] * 4 + [0] * 4)
box_y = array(
    "H",
    [
        bgr565(255, 0, 0),
        bgr565(255, 127, 0),
        bgr565(255, 255, 0),
        bgr565(255, 255, 63),
        bgr565(127, 255, 0),
        bgr565(0, 255, 0),
        bgr565(0, 255, 127),
        bgr565(63, 255, 255),
        bgr565(0, 255, 255),
        bgr565(0, 127, 255),
        bgr565(0, 0, 255),
        bgr565(63, 63, 255),
        bgr565(127, 0, 255),
        bgr565(255, 0, 255),
        bgr565(255, 0, 127),
        bgr565(255, 63, 63),
    ],
)


@micropython.viper
def scrolling_boxes(t: uint, y_min: uint):
    fb16 = ptr16(display)
    bxs = ptr16(box_x)
    bys = ptr16(box_y)
    if y_min == uint(0):
        idx = uint(0)
    else:
        idx = uint(HALF_SIZE)

    for y in range(y_min, y_min + HALF_HEIGHT):
        ty = uint(y + t)
        if uint(ty & 7) < uint(4):
            boxcol_idx = ty >> 3
            for x in range(WIDTH):
                fb16[idx] = uint(bxs[x & 7] & bys[((boxcol_idx + (x >> 3)) & 15)])
                idx += 1
        else:
            for x in range(WIDTH):
                fb16[idx] = 0
                idx += 1


WHITE = const(0xFFFF)
GREY75 = const(0xBDF7)
GREY50 = const(0x7BEF)
GREY25 = const(0x39E7)
GREY12 = const(0x18E3)


@micropython.viper
def checkernest(t: uint, y_min: uint):
    fb16 = ptr16(display)
    if y_min == uint(0):
        idx = uint(0)
    else:
        idx = uint(HALF_SIZE)

    t3 = t >> 2
    t2 = t >> 1
    t1 = t
    for y in range(y_min, y_min + HALF_HEIGHT):
        y1bit = ((y - t1) >> 5) & 1
        y2bit = ((y + t2) >> 4) & 1
        y3bit = ((y + t3) >> 3) & 1
        for x in range(WIDTH):
            fb16[idx] = uint(
                GREY25
                if ((x >> 5 & 1) ^ y1bit)
                else (
                    GREY12
                    if (((x - t1) >> 4 & 1) ^ y2bit)
                    else (GREY50 if (((x + t2) >> 3 & 1) ^ y3bit) else (0))
                )
            )
            idx += 1
