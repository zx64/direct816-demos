import math
import micropython
from array import array

max_pal = const(256)
palmask = const(max_pal - 1)


# Expected values 0..255
@micropython.viper
def rgb565(r: uint, g: uint, b: uint) -> uint:
    return ((r & 0b11111000) << 8 | (g & 0b11111100) << 3 | b >> 3) & 0xFFFF


# This is the format PicoVector stores colours in memory
@micropython.viper
def u32_rgb565(src: uint) -> uint:
    return (src & 0xF8) << 8 | (src & 0xFC00) >> 5 | (src & 0xF8_00_00) >> 19


# L: list[tuple[uint, uint, uint]]
def convert_palette(L):
    if len(L) > max_pal:
        raise ValueError(f"Palette is too large {len(L)} > {max_pal}")
    return array("H", [rgb565(*i) for i in L])


# f: Callable[[uint], tuple[uint, uint, uint]]
def generate_palette(f, count=max_pal):
    if count > max_pal:
        raise ValueError(f"Palette is too large {count} > {max_pal}")
    return array("H", [rgb565(*f(i)) for i in range(count)])


def load_palette(filename: str):
    temp = array("H", [0] * max_pal)
    with open(filename, "rb") as f:
        size = f.readinto(temp)
        if size > 512:
            raise ValueError(f"Palette is too large: {size / 2} > {max_pal}")

    return temp


def make_palette_cycle(palette):
    if len(palette) != max_pal:
        raise ValueError("Palette has to have {max_pal} entries")

    # Compact palette by discarding every other entry
    for i in range(128):
        palette[i] = palette[2 * i]

    # Convert upper half into a mirror of the first half
    for i in range(128):
        palette[255 - i] = palette[i]

    return palette


orange_cycle = make_palette_cycle(generate_palette(lambda i: (i, i // 4, i // 8)))
assert len(orange_cycle) == (palmask + 1)

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
def convert_pv_image16(img: object):
    iwidth = int(img.width)
    iheight = int(img.height)
    isize = uint(iwidth * iheight)

    pixels = array("H", [0 for _ in range(isize)])
    mask = array("B", [0 for _ in range(isize)])

    dst_width = uint(iheight)
    dst_height = uint(iwidth)

    src: ptr32 = ptr32(img)
    src_end: uint = uint(src) + isize * 4

    dst: ptr16 = ptr16(pixels)

    for y in range(iheight):
        for x in range(iwidth):
            p32 = uint(src[y * iwidth + x])
            p16: uint = (
                (p32 & 0xF8) << 8 | (p32 & 0xFC00) >> 5 | (p32 & 0xF8_00_00) >> 19
            )
            dst[x * iheight + y] = p16
            mask[x * iheight + y] = 1 if int(p32 >> 24) == 255 else 0

    return pixels, mask, dst_width, dst_height
