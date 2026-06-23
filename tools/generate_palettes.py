#!/usr/bin/env python
from array import array
from matplotlib_colourmaps import all_colourmaps
from vgapal import vga
from typehints import hsv, JustFloat, RGB_F32, RGB_U8


def rescale_rgb888(r: JustFloat, g: JustFloat, b: JustFloat) -> RGB_U8:
    return (int(r * 255), int(g * 255), int(b * 255))


def pack_rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0b11111_000) << 8 | (g & 0b111111_00) << 3 | b >> 3) & 0xFFFF


def unpack_rgb332(v: int) -> RGB_U8:
    return (v & 0b111_000_00), (v & 0b000_111_00) << 3, (v & 0b000_000_11) << 6


# Values in range [0..1] float
theta360 = [theta / 360.0 for theta in range(360)]
hsv_100_full: list[RGB_F32] = [hsv(h, 1.0, 1.0) for h in theta360]
hsv_75_full: list[RGB_F32] = [hsv(h, 0.75, 1.0) for h in theta360]

theta256 = [theta / 256.0 for theta in range(256)]
hsv_100: list[RGB_F32] = [hsv(h, 1.0, 1.0) for h in theta256]
hsv_75: list[RGB_F32] = [hsv(h, 0.75, 1.0) for h in theta256]

# TODO: oklch gradients

# Prescaled to [0..255] int
grey256: list[RGB_U8] = [(v, v, v) for v in range(256)]
rgb332: list[RGB_U8] = [unpack_rgb332(v) for v in range(256)]

# Gradients are stored in a subdirectory
gradients = {}
palettes = {}


def convert_palette(name: str, seq: list[RGB_U8]) -> array:
    if len(seq) < 256:
        raise ValueError("Too few colours")

    colours = [pack_rgb565(*c) for c in seq]

    if not name.endswith("_full"):
        assert len(colours) == 256

    return array("H", colours)


def add_gradient_int(name, colours: list[RGB_U8]):
    gradients[name] = convert_palette(name, colours)


def add_gradient(name, colours: list[RGB_F32]):
    palette: list[RGB_U8] = [rescale_rgb888(*c) for c in colours]
    gradients[name] = convert_palette(name, palette)


def add_palette(name, colours: list[RGB_U8]):
    palettes[name] = convert_palette(name, colours)


add_gradient("hsv_100", hsv_100)
add_gradient("hsv_75", hsv_75)
add_gradient("hsv_100_full", hsv_100_full)
add_gradient("hsv_75_full", hsv_75_full)
add_gradient_int("grey", grey256)
add_palette("rgb332", rgb332)
add_palette("vga", vga)

for name, cmap in all_colourmaps.items():
    add_gradient(name, cmap)


def generate_palettes():
    print("Special Palettes")
    for name, palette in sorted(palettes.items()):
        print(f"{name}: {len(palette)}")
        with open(f"../firmware/assets/palettes/{name}.bin", "wb") as out:
            out.write(palette)

    print("Gradient Palettes")
    for name, palette in sorted(gradients.items()):
        if name.endswith("_full"):
            continue
        print(f"{name}: {len(palette)}")
        with open(f"../firmware/assets/palettes/gradients/{name}.bin", "wb") as out:
            out.write(palette)


if __name__ == "__main__":
    generate_palettes()
