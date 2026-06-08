import os
from array import array

full_strip_width = const(256)
strip_width = const(64)
strip_height = const(16)
palette_dir = "/system/assets/palettes"

row_fg = const(0)
row_bg = const(1)
row_pal = const(2)
num_ui_rows = const(3)


def init():
    global font_width, font_height, row_height

    badge.mode(HIRES)
    screen.font = rom_font.nope
    font_width, font_height = screen.measure_text("W")
    row_height = max(strip_height, font_height) + 1

    global effect_names, palette_names, num_cols

    effect_names = [
        [  # Background effects
            "palette cycling",
            "simple xor",
            "scrolling xor",
            "plasma",
            "checkerboard rotozoom",
            "tunnel",
            "starfield",
        ],
        [  # Foreground effects
            "<no effect>",
            "bouncing balls",
            "brownian motion",
            "checkerboard rotozoom",
        ],
    ]
    try:
        palette_names = sorted(
            [filename.replace(".bin", "") for filename in os.listdir(palette_dir)]
        )
    except OSError:
        palette_names = ["default"]

    num_cols = [
        len(effect_names[0]),
        len(effect_names[1]),
        len(palette_names),
    ]
    assert len(num_cols) == num_ui_rows

    global effect_sprites, preview_palette_strips, full_palette_strips
    effect_sprites = {
        name: make_text_sprite(name) for name in set(effect_names[0] + effect_names[1])
    }

    preview_palette_strips = [
        make_palette_strip(name, strip_width, strip_height) for name in palette_names
    ]
    full_palette_strips = [
        make_palette_strip(name, full_strip_width, strip_height)
        for name in palette_names
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

        # Palette is a double height row
        y = screen.height - (num_ui_rows + 1) * row_height

        selected_row_y = y + self.ui_row * row_height
        # Draw selected row background
        screen.pen = color.navy
        if self.ui_row == 2:
            screen.rectangle(0, selected_row_y - 1, screen.width, 2 * row_height)
        else:
            screen.rectangle(0, selected_row_y - 1, screen.width, row_height + 1)

        y = self.draw_effect_selectors(y)
        y = self.draw_palette_selector(y)

    def draw_effect_selectors(self, y):
        screen.pen = color.green

        for layer in (row_fg, row_bg):
            max_idx = num_cols[layer]

            # Start with selected item in centre
            idx = self.selections[layer]
            spr = effect_sprites[effect_names[layer][idx]]
            x = (screen.width - spr.width) // 2
            max_left = x
            screen.rectangle(x, y, spr.width, spr.height)
            screen.blit(spr, vec2(x, y))
            x += spr.width + font_width

            # Now fill either side with the rest of the list

            # Right of selection
            while x < screen.width:
                idx = (idx + 1) % max_idx
                spr = effect_sprites[effect_names[layer][idx]]
                screen.blit(spr, vec2(x, y))
                x += spr.width + font_width

            # Left of selection
            x = max_left
            idx = self.selections[layer]
            while x > 0:
                idx = (idx - 1) % max_idx
                spr = effect_sprites[effect_names[layer][idx]]
                x -= spr.width + font_width
                screen.blit(spr, vec2(x, y))

            y += row_height

        return y

    def draw_palette_selector(self, y):
        max_idx = num_cols[row_pal]
        idx = self.selections[row_pal]

        # First row: selected palette in full
        x = (screen.width - full_strip_width) // 2
        spr = full_palette_strips[idx]
        screen.blit(spr, vec2(x, y))

        # Second row: preview of other available palettes
        y += row_height
        x = screen.width // 2 - strip_width // 8
        max_left = x
        x += strip_width // 4 + font_width

        while x < screen.width:
            idx = (idx + 1) % max_idx
            spr = preview_palette_strips[idx]
            screen.blit(spr, vec2(x, y))
            x += strip_width + font_width

        x = max_left
        idx = self.selections[row_pal]
        while x > 0:
            idx = (idx - 1) % max_idx
            spr = preview_palette_strips[idx]
            x -= strip_width + font_width
            screen.blit(spr, vec2(x, y))

        y += row_height
        return y
