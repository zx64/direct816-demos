import common_effects
import math
import micropython
from array import array
from common_effects import (
    convert_palette,
    generate_palette,
    make_palette_cycle,
    x_scroll,
    y_scroll,
)
from common_effects import orange_cycle as palette

WIDTH = const(240)
HEIGHT = const(320)
BYTES_PER_PIXEL = const(2)
HALF_HEIGHT = const(HEIGHT // 2)
SIZE = const(WIDTH * HEIGHT)
HALF_SIZE = const(SIZE // 2)

# These values are for calculating pointers to the middle and end of the buffer
# Unlike C, Viper pointer arithmetic always operates in bytes rather than sizeof(*p)
SIZE_BYTES = const(BYTES_PER_PIXEL * SIZE)
HALF_SIZE_BYTES = const(SIZE_BYTES // 2)


angle_bits = const(10)
angle_len = const(1 << angle_bits)
angle_mask = const(angle_len - 1)
assert angle_mask == common_effects.angle_mask
palmask = const(255)


@micropython.viper
def fill_565(v: uint):
    v16: uint = v & 0xFFFF
    v32: uint = v16 << 16 | v16
    fb32 = ptr32(display)
    end: uint = uint(fb32) + SIZE_BYTES
    while uint(fb32) != end:
        fb32[0] = v32
        fb32 = ptr32(uint(fb32) + 4)


@micropython.viper
def palcycle(t: uint, y_min: uint):
    fb32 = ptr32(display)
    pal = ptr16(palette)

    if y_min != uint(0):
        fb32 = ptr32(uint(fb32) + HALF_SIZE_BYTES)

    val16: uint = pal[t & palmask]
    val = val16 << 16 | val16
    end: uint = uint(fb32) + HALF_SIZE_BYTES
    while uint(fb32) != end:
        fb32[0] = val
        fb32 = ptr32(uint(fb32) + 4)


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
box_y = convert_palette(
    [
        (255, 0, 0),
        (255, 127, 0),
        (255, 255, 0),
        (255, 255, 63),
        (127, 255, 0),
        (0, 255, 0),
        (0, 255, 127),
        (63, 255, 255),
        (0, 255, 255),
        (0, 127, 255),
        (0, 0, 255),
        (63, 63, 255),
        (127, 0, 255),
        (255, 0, 255),
        (255, 0, 127),
        (255, 63, 63),
    ]
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


def pv_text(msg):
    fnt = rom_font.nope
    # TODO: get expected text dimensions for given font
    img = image(len(msg) * 7, fnt.height)
    img.antialias = X4
    img.font = fnt
    img.pen = color.rgb(0, 0, 0, 255)
    img.clear()
    img.pen = color.white
    img.text(msg, 0, 0)

    return img


def pv_square(side, color):
    img = image(side, side)
    img.pen = color
    img.clear()
    return img


pv_text = pv_text("Hello World!")
pv_red = pv_square(64, color.red)
pv_green = pv_square(32, color.green)
pv_blue = pv_square(16, color.blue)

from common_effects import convert_pv_image16


cvt_text = convert_pv_image16(pv_text)
cvt_red = convert_pv_image16(pv_red)
cvt_green = convert_pv_image16(pv_green)
cvt_blue = convert_pv_image16(pv_blue)


@micropython.viper
def blit_pv_image16(img, x: int, y: int):
    if x >= WIDTH:
        return
    if y >= HEIGHT:
        return

    iwidth = int(img[1])
    stride = uint(iwidth)
    x_skip = uint(0)
    if x < 0:
        iwidth += x
        x_skip = uint(-x)
        if iwidth <= 0:
            return
        x = 0
    if x + iwidth > WIDTH:
        iwidth = WIDTH - x

    iheight = int(img[2])
    y_skip = uint(0)
    if y < 0:
        iheight += y
        y_skip = uint(-y)
        if iheight <= 0:
            return
        y = 0
    if y + iheight > HEIGHT:
        iheight = HEIGHT - y

    origin = x + WIDTH * y
    src_pixels = iwidth * iheight

    src = ptr16(uint(ptr16(img[0])) + (x_skip + y_skip * stride) * BYTES_PER_PIXEL)
    dst = ptr16(uint(ptr16(display)) + origin * BYTES_PER_PIXEL)

    for py in range(iheight):
        for px in range(iwidth):
            dst[px + py * WIDTH] = src[px + py * stride]


@micropython.viper
def test_blit16(t: uint, y_min: uint):
    if y_min != uint(0):
        return

    fill_565(GREY25)
    sx = int(t - 32) % (WIDTH + 32)
    sy = int(t - 32) % (HEIGHT + 32)
    blit_pv_image16(cvt_red, sx, 0)
    blit_pv_image16(cvt_green, 0, sy)
    blit_pv_image16(cvt_blue, sx, sy)
    blit_pv_image16(cvt_text, WIDTH - sx, HEIGHT - sy)
