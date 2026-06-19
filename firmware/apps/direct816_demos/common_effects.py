import math
from array import array
from direct816 import make_palette_cycle, generate_palette


orange_cycle = make_palette_cycle(generate_palette(lambda i: (i, i // 4, i // 8)))

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
