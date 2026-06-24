from time import ticks_us

SCREEN_WIDTH = const(240)
SCREEN_HEIGHT = const(320)
HALF_HEIGHT = const(SCREEN_HEIGHT // 2)

screen_bounds = rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
core_bounds = [
    rect(0, 0, SCREEN_WIDTH, HALF_HEIGHT),
    rect(0, HALF_HEIGHT, SCREEN_WIDTH, HALF_HEIGHT),
]


class Effect:
    def handle_input(self, tick: int, dT: float):
        pass

    def update(self, tick: int, dT: float, core1: bool):
        pass

    # scroll uses logical coordinates: can be negative, can be greater than screen bounds
    # dest uses screen coordinates, caller's responsibility to ensure correct clipping
    def draw(self, scroll: vec2, dest: rect, core1: bool):
        pass

    def set_palette(self, palette, layer):
        # D16 effects don't need palettes, but can use them as e.g. precalculated gradients
        pass


class Layer:
    def __init__(self, effect, dest=None, scroll=None):
        if effect is None:
            raise ValueError("Effect can not be None")
        self.effect = effect
        self.dests = [None, None]
        self.set_dest(dest or screen_bounds)
        self.scroll = scroll or vec2()

    def draw(self, core1: bool):
        self.effect.draw(self.scroll, self.dests[core1], core1)

    def set_dest(self, dest: rect):
        self.dests[0] = dest.intersection(core_bounds[0])
        self.dests[1] = dest.intersection(core_bounds[1])


class EffectManager:
    def __init__(self):
        self.foreground_effects = {}
        self.background_effects = {}
        self.invalid_menu_text = True
        self.layers = [None, None]
        self.ticks = 0
        self.last_update = ticks_us()

    def update(self):
        now = ticks_us()
        dT = (now - self.last_update) / 1000.0
        self.last_update = now
        if self.invalid_menu_text:
            self.prepare_menus()

        for layer in self.layers:
            if not layer:
                continue
            layer.effect.handle_input(self.ticks, dT)
            layer.effect.update(self.ticks, dT, False)
            layer.effect.update(self.ticks, dT, True)

        for layer in self.layers:
            if not layer:
                continue
            layer.draw(False)
            layer.draw(True)

        self.ticks += 1

    def register_foreground_effect(self, effect: Effect):
        self.foreground_effects[effect.__class__.__name__] = effect
        self.invalid_menu_text = True

    def register_background_effect(self, effect: Effect):
        self.background_effects[effect.__class__.__name__] = effect
        self.invalid_menu_text = True

    def set_background(self, effect_class: type):
        self.layers[0] = Layer(self.background_effects[effect_class.__name__])

    def set_foreground(self, effect_class: type):
        self.layers[1] = Layer(self.foreground_effects[effect_class.__name__])

    def prepare_menus(self):
        self.invalid_menu_text = False
        print("Foreground effects: ", end="")
        print(",".join(sorted(k for k in self.foreground_effects.keys())))
        print("Background effects: ", end="")
        print(",".join(sorted(k for k in self.background_effects.keys())))


class DummyEffect(Effect):
    def __init__(self, v):
        self.v = v

    def update(self, tick: int, dT: float, core1: bool):
        print(f"[{self.v}] {core1=} Updating {tick=} {dT=:.2f}")

    def draw(self, scroll: vec2, dest: rect, core1: bool):
        print(f"[{self.v}] {core1=} Drawing to {dest} with scroll offset {scroll}")


em = EffectManager()
em.update()
print(".")
em.register_background_effect(DummyEffect(0))
em.register_foreground_effect(DummyEffect(1))
em.update()
print(".")
em.set_background(DummyEffect)
em.update()
print(".")
em.set_foreground(DummyEffect)
em.update()
print(".")
em.update()
print(".")
em.update()
print(".")
