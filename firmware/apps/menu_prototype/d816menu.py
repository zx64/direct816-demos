import os
from array import array

strip_width = const(64)
strip_height = const(16)
palette_dir = "/system/assets/palettes"


def init():
    badge.mode(HIRES)
    screen.font = rom_font.nope

    global effect_names, palette_names

    effect_names = [
        "palette cycling",
        "simple xor",
        "scrolling xor",
        "plasma",
        "zooming checkerboards",
    ]
    try:
        palette_names = sorted(
            [filename.replace(".bin", "") for filename in os.listdir(palette_dir)]
        )
    except OSError:
        palette_names = ["default"]

    global font_width, font_height

    font_width, font_height = screen.measure_text("W")

    global preview_palette_strips, full_palette_strips
    preview_palette_strips = [
        make_palette_strip(name, strip_width, strip_height) for name in palette_names
    ]
    full_palette_strips = [
        make_palette_strip(name, 256, strip_height) for name in palette_names
    ]


def make_palette_strip(name, w, h):
    img = image(w, h)
    palette = array("H", [0] * 256)
    try:
        with open(f"{palette_dir}/{name}.bin", "rb") as f:
            size = f.readinto(palette)
            if size > 512:
                raise ValueError(f"Palette is too large: {size / 2} > 256")
    except OSError:
        img.pen = color.red
        img.font = screen.font
        img.text("ERR", 0, 0)
        return img

    x = 0
    for pal_idx in range(0, len(palette), len(palette) // w):
        rgb565 = palette[pal_idx]
        r = (rgb565 & 0b11111_000000_00000) >> 8
        g = (rgb565 & 0b00000_111111_00000) >> 3
        b = (rgb565 & 0b00000_000000_11111) << 3
        img.pen = color.rgb(r, g, b)
        img.rectangle(x, 0, 1, h)
        x += 1

    return img


class D816Menu:
    def __init__(self):
        self.effect_idx = 0
        self.palette_idx = 0
        self.visible = True

    def up(self):
        if not self.visible:
            self.visible = True
        self.palette_idx = (self.palette_idx - 1) % len(palette_names)
        print(palette_names[self.palette_idx])

    def down(self):
        if not self.visible:
            self.visible = True
        self.palette_idx = (self.palette_idx + 1) % len(palette_names)
        print(palette_names[self.palette_idx])

    def left(self):
        if not self.visible:
            self.visible = True
        self.effect_idx = (self.effect_idx - 1) % len(effect_names)
        print(effect_names[self.effect_idx])

    def right(self):
        if not self.visible:
            self.visible = True
        self.effect_idx = (self.effect_idx + 1) % len(effect_names)
        print(effect_names[self.effect_idx])

    def ok(self):
        self.visible = not self.visible

    def display(self):
        if not self.visible:
            return

        screen.pen = color.grey
        x, y = 0, 3 * screen.height // 4 - font_height // 2
        for idx, name in enumerate(effect_names):
            w, h = screen.measure_text(name)
            if idx == self.effect_idx:
                screen.rectangle(x, y, w, h)
                screen.pen = color.white
            screen.text(name, x, y)
            if idx == self.effect_idx:
                screen.pen = color.grey
            x += w + font_width

        r = rect(screen.width - strip_width - 2, 0, strip_width, strip_height)
        for idx, preview in enumerate(preview_palette_strips):
            if idx == self.palette_idx:
                screen.blit(
                    full_palette_strips[idx],
                    rect(screen.width - 256, r.y, 256, strip_height),
                )
            else:
                screen.blit(preview, r)
            r.y += strip_height
