#!/usr/bin/python

import math
from array import array
from PIL import Image, ImageDraw

# TODO:
# Extract my palette conversion code from other projects
#
# Generate Doom-era palette-to-palette lookups for things like brightness adjusting,
# applying tints, full screen effects or finding the best match for 50% transluscency
# between two colours
#
# Palette expansion for smaller palettes (smoother blends etc.)


def pack_rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0b11111000) << 8 | (g & 0b11111100) << 3 | b >> 3) & 0xFFFF


def unpack_rgb565(rgb565: int) -> tuple[int, int, int]:
    r = (rgb565 & 0b11111_000000_00000) >> 8
    g = (rgb565 & 0b00000_111111_00000) >> 3
    b = (rgb565 & 0b00000_000000_11111) << 3
    return r, g, b


def lerp(a: int, b: int, t: float) -> int:
    return int((a & 0xFF) + ((b & 0xFF) - (a & 0xFF)) * t)


def blend_rgb565(c1: int, c2: int, alpha: float) -> int:
    r1, g1, b1 = unpack_rgb565(c1)
    r2, g2, b2 = unpack_rgb565(c2)
    return pack_rgb565(
        lerp(r1, r2, alpha),
        lerp(g1, g2, alpha),
        lerp(b1, b2, alpha),
    )


def preview_palette(palette: array, tile_size=16, gutter=2) -> Image.Image:
    tiles_per_line = math.ceil(math.sqrt(len(palette)))
    tile_step = tile_size + gutter
    grid_side_length = tiles_per_line * tile_step
    header_step = 18
    image_side_length = grid_side_length + header_step

    im = Image.new("RGB", (image_side_length, image_side_length))
    draw = ImageDraw.Draw(im)
    for i in range(tiles_per_line):
        draw.text(((i + 1) * header_step, 0), f"{i:02X}")
        draw.text((0, (i + 1) * header_step), f"{i * tiles_per_line:02X}")
    x, y = header_step, header_step
    for rgb565 in palette:
        draw.rectangle([x, y, x + tile_size, y + tile_size], fill=unpack_rgb565(rgb565))
        x += tile_step
        if x >= header_step + grid_side_length:
            x = header_step
            y += tile_step
    im.show()
    return im


def relative_luminance(r: int, g: int, b: int) -> float:
    """
    https://en.wikipedia.org/wiki/Relative_luminance
    """
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def set_rgb(r: int, g: int, b: int) -> str:
    """
    Generates the terminal codes to set background to given colour and foreground to
    something readable.

    Foreground colour is picked according to a simple threshold
    """
    if relative_luminance(r, g, b) < 128:
        fg = 255
    else:
        fg = 0
    return f"\x1b[38;2;{fg};{fg};{fg}m\x1b[48;2;{r};{g};{b}m"


reset_rgb = "\x1b[39m\x1b[49m"


def print_palette(palette: array):
    tiles_per_line = math.ceil(math.sqrt(len(palette)))

    print("   ", end="")
    for column in range(tiles_per_line):
        print(f"  {column:02X} ", end="")
    print()
    idx = 0
    for row in range(tiles_per_line):
        print(f"{row * tiles_per_line:02X} ", end="")
        for _ in range(tiles_per_line):
            rgb565 = palette[idx]
            r, g, b = unpack_rgb565(rgb565)
            print(f"{set_rgb(r, g, b)}{rgb565:04X}{reset_rgb} ", end="")
            idx += 1
        print()


if __name__ == "__main__":
    greys = array("H", [pack_rgb565(i, i, i) for i in range(256)])
    print_palette(greys)
    tmp = array("H", [0] * 256)
    for i in range(256):
        tmp[i] = blend_rgb565(0, 0xFFFF, i / 255.0)
    print_palette(tmp)

    with open("../firmware/assets/palettes/gradients/viridis.bin", "rb") as f:
        f.readinto(tmp)
    print_palette(tmp)

    with open("../firmware/assets/palettes/vga.bin", "rb") as f:
        f.readinto(tmp)
    print_palette(tmp)
