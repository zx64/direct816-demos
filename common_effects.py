import math
import micropython
from array import array


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
    if len(L) > 256:
        raise ValueError(f"Palette is too large {len(L)} > 256")
    return array("H", [rgb565(*i) for i in L])


# f: Callable[[uint], tuple[uint, uint, uint]]
def generate_palette(f, count=256):
    if count > 256:
        raise ValueError(f"Palette is too large {count} > 256")
    return array("H", [rgb565(*f(i)) for i in range(count)])


def load_palette(filename: str):
    temp = array("H", [0] * 256)
    with open(filename, "rb") as f:
        size = f.readinto(temp)
        if size > 512:
            raise ValueError(f"Palette is too large: {size / 2} > 256")

    return temp


def make_palette_cycle(palette):
    if len(palette) != 256:
        raise ValueError("Palette has to have 256 entries")

    # Compact palette by discarding every other entry
    for i in range(128):
        palette[i] = palette[2 * i]

    # Convert upper half into a mirror of the first half
    for i in range(128):
        palette[255 - i] = palette[i]

    return palette


orange_cycle = make_palette_cycle(generate_palette(lambda i: (i, i // 4, i // 8)))
palmask = const(255)
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
