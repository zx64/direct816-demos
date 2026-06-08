import os
from array import array

strip_width = const(64)
strip_height = const(16)
palette_dir = "/system/assets/palettes"


def init():
    global font_width, font_height

    badge.mode(HIRES)
    screen.font = rom_font.nope
    font_width, font_height = screen.measure_text("W")

    global background_effect_names, foreground_effect_names, palette_names, num_cols

    background_effect_names = [
        "palette cycling",
        "simple xor",
        "scrolling xor",
        "plasma",
        "checkerboard rotozoom",
    ]
    foreground_effect_names = ["<no effect>", "checkerboard rotozoom"]
    try:
        palette_names = sorted(
            [filename.replace(".bin", "") for filename in os.listdir(palette_dir)]
        )
    except OSError:
        palette_names = ["default"]

    num_cols = [
        len(background_effect_names),
        len(foreground_effect_names),
        len(palette_names),
    ]

    global effect_sprites, preview_palette_strips, full_palette_strips, ui_labels
    effect_sprites = {
        name: make_text_sprite(name)
        for name in set(background_effect_names + foreground_effect_names)
    }
    ui_labels = [make_text_sprite(text) for text in ["bg: ", "fg: ", "pal: "]]

    preview_palette_strips = [
        make_palette_strip(name, strip_width, strip_height) for name in palette_names
    ]
    full_palette_strips = [
        make_palette_strip(name, 256, strip_height) for name in palette_names
    ]


def make_text_sprite(text, colour=color.white):
    size = screen.measure_text(text)
    img = image(int(size[0]), int(size[1]))
    img.pen = colour
    img.font = screen.font
    img.text(text, 0, 0)
    return img


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


num_ui_rows = const(3)


class D816Menu:
    def __init__(self):
        self.selections = [0, 0, 0]
        self.ui_row = 0
        self.visible = True

    def up(self):
        if not self.visible:
            self.visible = True
        self.ui_row = (self.ui_row - 1) % num_ui_rows

    def down(self):
        if not self.visible:
            self.visible = True
        self.ui_row = (self.ui_row + 1) % num_ui_rows

    def left(self):
        if not self.visible:
            self.visible = True
        row = self.ui_row
        self.selections[row] = (self.selections[row] - 1) % num_cols[row]

    def right(self):
        if not self.visible:
            self.visible = True
        row = self.ui_row
        self.selections[row] = (self.selections[row] + 1) % num_cols[row]

    def ok(self):
        self.visible = not self.visible

    def display(self):
        if not self.visible:
            return

        x, y = 0, 3 * screen.height // 4 - font_height // 2
        selected_row_y = y + self.ui_row * font_height
        screen.pen = color.navy
        screen.rectangle(0, selected_row_y - 1, screen.width, font_height + 2)
        screen.pen = color.green

        # Effects selectors
        screen.blit(ui_labels[0], vec2(x, y))
        x += ui_labels[0].width
        for idx, name in enumerate(background_effect_names):
            spr = effect_sprites[name]
            if idx == self.selections[0]:
                screen.rectangle(x, y, spr.width, spr.height)
            screen.blit(effect_sprites[name], vec2(x, y))
            x += spr.width + font_width

        x = 0
        y += font_height
        screen.blit(ui_labels[1], vec2(x, y))
        x += ui_labels[1].width
        for idx, name in enumerate(foreground_effect_names):
            spr = effect_sprites[name]
            if idx == self.selections[1]:
                screen.rectangle(x, y, spr.width, spr.height)
            screen.blit(effect_sprites[name], vec2(x, y))
            x += spr.width + font_width

        # Palette selector
        x = 0
        y += font_height
        screen.blit(ui_labels[2], vec2(x, y))
        x += ui_labels[2].width
        for idx, preview in enumerate(preview_palette_strips):
            if idx == self.selections[2]:
                spr = full_palette_strips[idx]
            else:
                spr = preview
            screen.blit(spr, vec2(x, y))
            x += spr.width + font_width
