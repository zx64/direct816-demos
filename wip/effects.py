import _thread
from time import sleep, ticks_us

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


class MTWorker:
    def __init__(self):
        self.lock = _thread.allocate_lock()
        self.running = True
        self.queue = []

        def worker(self):
            from time import sleep

            while True:
                with self.lock:
                    if not self.running:
                        return
                    if not self.queue:
                        sleep(0)
                        continue
                    func, args = self.queue.pop()
                func(*args)

        _thread.start_new_thread(worker, (self,))

    def empty(self):
        with self.lock:
            return not self.queue

    def call(self, func, *args):
        with self.lock:
            self.queue.append((func, args))

    def stop(self):
        with self.lock:
            self.running = False


class EffectManager:
    def __init__(self, mt):
        self.mt = mt
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
            self.mt.call(layer.effect.update, self.ticks, dT, True)
            layer.effect.update(self.ticks, dT, False)

        while not self.mt.empty():
            sleep(0)

        for layer in self.layers:
            if not layer:
                continue
            self.mt.call(layer.draw, True)
            layer.draw(False)

        while not self.mt.empty():
            sleep(0)

        self.ticks += 1

    def register_foreground_effect(self, name: str, effect: Effect):
        if name in self.foreground_effects:
            raise RuntimeError(f"Duplicate effect name {name} for this layer")
        self.foreground_effects[name] = effect
        self.invalid_menu_text = True

    def register_background_effect(self, name: str, effect: Effect):
        if name in self.background_effects:
            raise RuntimeError(f"Duplicate effect name {name} for this layer")
        self.background_effects[name] = effect
        self.invalid_menu_text = True

    def set_background(self, name: str):
        self.layers[0] = Layer(self.background_effects[name])

    def set_foreground(self, name: str):
        self.layers[1] = Layer(self.foreground_effects[name])

    def prepare_menus(self):
        self.invalid_menu_text = False
        print("Foreground effects: ", end="")
        print(",".join(sorted(k for k in self.foreground_effects.keys())))
        print("Background effects: ", end="")
        print(",".join(sorted(k for k in self.background_effects.keys())))

    def dbg(self):
        for layer in self.layers:
            if not layer:
                continue
            layer.effect.print_msgs()


start = ticks_us()


class DummyEffect(Effect):
    def __init__(self, v):
        self.v = v
        self.last_update = [0, 0]
        self.last_draw = [0, 0]
        self.update_msgs = ["", ""]
        self.draw_msgs = ["", ""]

    def update(self, tick: int, dT: float, core1: bool):
        self.last_update[core1] = ticks_us() - start
        self.update_msgs[core1] = (
            f"[{ticks_us() - start}][{self.v}] {core1=} Updating {tick=} {dT=:.2f}"
        )

    def draw(self, scroll: vec2, dest: rect, core1: bool):
        self.last_draw[core1] = ticks_us() - start
        self.draw_msgs[core1] = (
            f"[{ticks_us() - start}][{self.v}] {core1=} Drawing to {dest} with scroll offset {scroll}"
        )

    def print_msgs(self):
        assert all(all(u < d for u in self.last_update) for d in self.last_draw)
        print("Update messages:")
        print(self.update_msgs[0])
        print(self.update_msgs[1])
        print("Draw messages:")
        print(self.draw_msgs[0])
        print(self.draw_msgs[1])


mt = MTWorker()
em = EffectManager(mt)
em.update()
em.dbg()
print(".")
em.register_background_effect("Dummy BG", DummyEffect("BG"))
em.update()
em.dbg()
print(".")
em.register_foreground_effect("Dummy FG", DummyEffect("FG"))
em.update()
em.dbg()
print(".")
em.set_background("Dummy BG")
em.update()
em.dbg()
print(".")
em.set_foreground("Dummy FG")
em.update()
em.dbg()
print(".")
em.update()
em.dbg()
print(".")
em.update()
em.dbg()
print(".")
mt.stop()
