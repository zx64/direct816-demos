# TODO
# Effect menu, button inputs
# Firmware changes:
# Get PicoGraphics or PicoVector working
import gc
import micropython
import direct16_effects
from array import array
from time import ticks_us

update = display.update
display.direct16(True)  # requires changes made locally
# display.set_vsync(False)
WIDTH = const(240)
HEIGHT = const(320)
HALF_HEIGHT = const(HEIGHT // 2)
SIZE = const(WIDTH * HEIGHT)
HALF_SIZE = const(SIZE // 2)
effect_duration = const(511)
assert len(memoryview(display)) == SIZE * 2


# Names for the index into the shared array
SHARED_TICK = const(0)
SHARED_DRAWIDX = const(1)

# [("name", <function>), ...]
drawfuncs = []


def get_drawfuncs(module, prefix, names):
    return [(f"{prefix}: {name}", getattr(module, name)) for name in names]


try:
    import _direct16_effects

    _direct16_effects.set_display(display)
    _direct16_effects.set_palette(direct16_effects.palette)
    _direct16_effects.set_scroll_arrays(
        direct16_effects.x_scroll, direct16_effects.y_scroll
    )
    drawfuncs.extend(
        get_drawfuncs(
            _direct16_effects,
            "native",
            ["palcycle", "simplexor", "xor_scroll", "plasma_scroll", "random_noise"],
        )
    )
except ImportError:
    pass

drawfuncs.extend(
    get_drawfuncs(
        direct16_effects,
        "viper",
        [
            "palcycle",
            "simple_xor",
            "xor_scroll",
            "plasma_scroll",
            "scrolling_boxes",
            "checkernest",
        ],
    )
)


def main(drawfuncs):
    import _thread

    lock = _thread.allocate_lock()
    t = array("I", [0, 0])

    def threadfunc(t):
        last_t = -1
        last_drawidx = -1
        drawfunc = None
        while True:
            lock.acquire()
            if t[SHARED_DRAWIDX] != last_drawidx:
                last_drawidx = t[SHARED_DRAWIDX]
                if last_drawidx < 0:
                    lock.release()
                    return
                drawfunc = drawfuncs[last_drawidx][1]
            if t[SHARED_TICK] != last_t:
                last_t = t[SHARED_TICK]
                drawfunc(last_t, HALF_HEIGHT)
            lock.release()

    df_name, drawfunc = drawfuncs[t[SHARED_DRAWIDX]]
    print(f"{df_name}")
    draw_duration = 0
    present_duration = 0
    _thread.start_new_thread(threadfunc, (t,))
    done = False

    while True:
        start = ticks_us()
        drawfunc(t[SHARED_TICK], 0)
        lock.acquire()
        draw_duration += ticks_us() - start
        draw_duration >>= 1
        if done:
            t[SHARED_TICK] = -1
            lock.release()
            return
        t[SHARED_TICK] += 1

        start = ticks_us()
        update()
        present_duration += ticks_us() - start
        present_duration >>= 1

        if t[SHARED_TICK] & effect_duration == 0:
            new_idx = t[SHARED_DRAWIDX] = (t[SHARED_DRAWIDX] + 1) % len(drawfuncs)
            df_name, drawfunc = drawfuncs[new_idx]
            print(f"avg draw: {draw_duration:<10} avg present: {present_duration}")
            print(f"{df_name}")
            draw_duration = 0
            present_duration = 0

        lock.release()
        if t[SHARED_TICK] & 31 == 0:
            if draw_duration > 0:
                print(f"avg draw: {draw_duration:<10} avg present: {present_duration}")
            gc.collect()


# main(get_drawfuncs(_direct16_effects, "native", ["xor_scroll", "plasma_scroll"]))
main(drawfuncs)
