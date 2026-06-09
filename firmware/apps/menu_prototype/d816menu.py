import os
from array import array

full_strip_width = const(256)
preview_strip_width = const(64)
strip_height = const(16)
strip_gap = 4
palette_dir = "/system/assets/palettes"

row_colours = [
    color.rgb(0x30, 0x34, 0x6D, 0xFF),  # color.navy
    color.rgb(0x40, 0x44, 0x7D, 0xFF),
    color.rgb(0x50, 0x54, 0x8D, 0xFF),
    color.rgb(0x60, 0x64, 0x9D, 0xFF),
    color.rgb(0x70, 0x74, 0xAD, 0xFF),  # start of flash
]

row_change_frames = const(4)
assert row_change_frames == len(row_colours) - 1


class TextStrip:
    def __init__(self, texts):
        if not texts:
            raise ValueError("Empty list")

        starts = [0] * len(texts)
        widths = [0] * len(texts)
        x = 0
        h = int(screen.measure_text(texts[0])[1] + 1)
        for idx, text in enumerate(texts):
            w = int(screen.measure_text(text)[0] + 1)
            starts[idx] = x
            widths[idx] = w

            x += w + column_gap

        img = image(x, h)
        img.font = screen.font
        for idx, text in enumerate(texts):
            img.pen = color.black
            img.text(text, starts[idx] + 1, 1)
            img.pen = color.white
            img.text(text, starts[idx], 0)

        self.img = img
        self.starts = starts
        self.widths = widths
        self.height = h


class PaletteStrip:
    def __init__(self, palettes, w, h, gap):
        if not palettes:
            raise ValueError("Empty list")
        if w < 1:
            raise ValueError("Invalid width")
        if h < 1:
            raise ValueError("Invalid height")

        img = image((gap + w) * len(palettes), h)
        starts = [(gap + w) * i for i in range(len(palettes))]
        for idx, palname in enumerate(palettes):
            palette = array("H", [0] * 256)
            try:
                filename = f"{palette_dir}/{palname}.bin"
                with open(filename, "rb") as f:
                    size = f.readinto(palette)
                    if size > 512:
                        raise ValueError(
                            f"Palette {palname} is too large: {size / 2} > 256"
                        )
            except OSError as err:
                raise OSError(f"Error opening {palname}") from err

            x = starts[idx]
            for pal_idx in range(0, len(palette), len(palette) // w):
                rgb565 = palette[pal_idx]
                r = (rgb565 & 0b11111_000000_00000) >> 8
                g = (rgb565 & 0b00000_111111_00000) >> 3
                b = (rgb565 & 0b00000_000000_11111) << 3
                img.pen = color.rgb(r, g, b)
                img.rectangle(x, 0, 1, h)
                x += 1

        self.img = img
        self.starts = starts
        self.widths = [w for _ in range(len(palettes))]
        self.height = h


row_fg = const(0)
row_bg = const(1)
row_pal = const(2)
num_ui_rows = const(3)


def init():
    global font_width, font_height, column_gap, row_height

    badge.mode(HIRES)
    screen.font = rom_font.nope
    font_width, font_height = screen.measure_text("W")
    column_gap = int(font_width + 2)
    row_height = int(max(strip_height, font_height) + 1)

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
        print(
            "Could not find palette directory, make sure you have copied the assets directory!"
        )
        raise

    num_cols = [
        len(effect_names[0]),
        len(effect_names[1]),
        len(palette_names),
    ]
    assert len(num_cols) == num_ui_rows

    global menu_strips, full_palettes
    menu_strips = [
        TextStrip(effect_names[0]),
        TextStrip(effect_names[1]),
        PaletteStrip(palette_names, preview_strip_width, strip_height, strip_gap),
    ]

    full_palettes = PaletteStrip(palette_names, full_strip_width, strip_height, 0)


class D816Menu:
    def __init__(self):
        self.selections = [0, 0, 0]
        self.ui_row = 0

        self.previous_selections = [0, 0, 0]

        self.row_change_timer = 0

        self.visible = True

    def up(self):
        if not self.visible:
            self.visible = True
        self.row_change_timer = row_change_frames
        self.ui_row = (self.ui_row - 1) % num_ui_rows

    def down(self):
        if not self.visible:
            self.visible = True
        self.row_change_timer = row_change_frames
        self.ui_row = (self.ui_row + 1) % num_ui_rows

    def left(self):
        if not self.visible:
            self.visible = True
        row = self.ui_row
        self.previous_selections[row] = self.selections[row]
        self.selections[row] = (self.selections[row] - 1) % num_cols[row]

    def right(self):
        if not self.visible:
            self.visible = True
        row = self.ui_row
        self.previous_selections[row] = self.selections[row]
        self.selections[row] = (self.selections[row] + 1) % num_cols[row]

    def ok(self):
        self.visible = not self.visible

    def menu_base_y(self):
        # Palette is a double height row
        return screen.height - (num_ui_rows + 1) * row_height

    def display(self):
        if not self.visible:
            return

        y = self.menu_base_y()

        # Draw selected row background
        screen.pen = row_colours[self.row_change_timer]

        # Flash the new row for one frame
        if self.row_change_timer > 0:
            self.row_change_timer -= 1

        selected_row_y = y + self.ui_row * row_height - 1
        if self.ui_row == 2:
            screen.rectangle(0, selected_row_y, screen.width, 2 * row_height)
        else:
            screen.rectangle(0, selected_row_y, screen.width, row_height + 1)

        y = self.draw_selectors(y)
        self.draw_current_palette(y)

    def draw_selectors(self, y):
        screen.pen = color.green

        for layer in (row_fg, row_bg, row_pal):
            strip = menu_strips[layer]

            # Start with selected item in centre
            idx = self.selections[layer]
            w = strip.widths[idx]
            start = strip.starts[idx]
            x = (screen.width - w) // 2
            screen.rectangle(x - 1, y - 1, w + 2, strip.height + 2)
            x -= start

            screen.blit(strip.img, vec2(x, y))

            # Make the strip wrap to fill any gaps either side after scrolling
            if x > 0:
                x -= strip.img.width
                screen.blit(strip.img, vec2(x, y))
            elif x + strip.img.width < screen.width:
                x += strip.img.width
                screen.blit(strip.img, vec2(x, y))

            y += row_height

        return y

    def draw_current_palette(self, y):
        idx = self.selections[row_pal]
        src = rect(full_palettes.starts[idx], 0, full_strip_width, strip_height)
        dst = rect(
            (screen.width - full_strip_width) // 2, y, full_strip_width, strip_height
        )
        screen.blit(full_palettes.img, src, dst)
