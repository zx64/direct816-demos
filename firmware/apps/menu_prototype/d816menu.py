import os


effect_names = ["abc", "defg", "hijkl", "mnopq"]
palette_dir = "/system/assets/palettes"
try:
    palette_names = [
        filename.replace(".bin", "") for filename in os.listdir(palette_dir)
    ]
except OSError:
    palette_names = ["default"]
font_width, font_height = screen.measure_text("W")


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

        x, y = screen.width - 4, 0
        for idx, name in enumerate(palette_names):
            w, h = screen.measure_text(name)
            if idx == self.palette_idx:
                screen.rectangle(x - w, y, w, h)
                screen.pen = color.white
            screen.text(name, x - w, y)
            if idx == self.palette_idx:
                screen.pen = color.grey
            y += h
