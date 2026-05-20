# TODO
# Merge common logic with test_direct16
# Dual layer support for drawfuncs
import gc
import micropython
import direct16_effects
from array import array
from time import ticks_us

update = display.update
dual_layer = const(1)
display.direct8(True, dual_layer)  # requires changes made locally
display.direct8_palette(direct16_effects.palette, 0)
if dual_layer:
    from direct16_effects import bgr565

    l1_palette = array(
        "H",
        [bgr565(i // 8, i, i // 4) for i in range(0, 256, 2)]
        + [bgr565(i // 8, i, i // 4) for i in range(255, 0, -2)],
    )
    display.direct8_palette(l1_palette, 1)

# display.set_vsync(False)
WIDTH = const(240)
HEIGHT = const(320)
HALF_HEIGHT = const(HEIGHT // 2)
SIZE = const(WIDTH * HEIGHT)
HALF_SIZE = const(SIZE // 2)
U32_SIZE = const(SIZE // 4)
HALF_U32_SIZE = const(U32_SIZE // 2)
effect_duration = const(511)
assert len(memoryview(display)) == 2 * SIZE if dual_layer else SIZE


@micropython.viper
def fill8(c: uint):
    fb32 = ptr32(display)
    c = c & 0xFF
    v32 = c << 24 | c << 16 | c << 8 | c
    for idx in range(U32_SIZE):
        fb32[idx] = v32


if dual_layer:

    @micropython.viper
    def fill8_both_layers(c: uint):
        fb32 = ptr32(display)
        c = c & 0xFF
        v32 = c << 24 | c << 16 | c << 8 | c
        for idx in range(U32_SIZE * 2):
            fb32[idx] = v32

    @micropython.viper
    def fill8_upper(c: uint):
        fb32 = ptr32(display)
        c = c & 0xFF
        v32 = c << 24 | c << 16 | c << 8 | c
        for idx in range(U32_SIZE, U32_SIZE * 2):
            fb32[idx] = v32


@micropython.viper
def palcycle(t: uint, y_min: uint):
    fb32 = ptr32(display)

    if y_min == uint(0):
        base = uint(0)
    else:
        base = uint(HALF_U32_SIZE)

    c = t & 0xFF
    v32 = c << 24 | c << 16 | c << 8 | c
    for idx in range(base, base + HALF_U32_SIZE):
        fb32[idx] = v32


@micropython.viper
def simple_xor(t: uint, y_min: uint):
    fb = ptr8(display)

    if y_min == uint(0):
        idx = uint(0)
    else:
        idx = uint(HALF_SIZE)

    for y in range(y_min, y_min + HALF_HEIGHT):
        for x in range(WIDTH):
            c = ((x ^ y) + t) & 0xFF
            fb[idx] = c
            idx += 1


if dual_layer:
    # Picking these makes the checker scroll line up nicely with the simple_xor background
    SKIP_X = const(64)
    SKIP_X2 = const(48)

    @micropython.viper
    def layer1_checker_scroll(t: uint, y_min: uint):
        _direct8_effects.xor_scroll(t, y_min)
        fb = ptr8(display)

        if y_min == uint(0):
            idx = uint(SIZE)
        else:
            idx = uint(SIZE + HALF_SIZE)

        val = t & 0xFF
        if val == uint(0):
            val = uint(1)
        for y in range(y_min, y_min + HALF_HEIGHT):
            y1bit = uint(((y + t) >> 4) & 1)
            idx += uint(SKIP_X)
            for x in range(SKIP_X, WIDTH - SKIP_X2):
                xbit = ((x - t) >> 4 & 1) ^ y1bit
                if xbit:
                    fb[idx] = val
                else:
                    fb[idx] = 0
                idx += 1
            idx += uint(SKIP_X2)


# Names for the index into the shared array
SHARED_TICK = const(0)
SHARED_DRAWIDX = const(1)

# [("name", <function>), ...]
drawfuncs = []


def get_drawfuncs(module, prefix, names):
    return [(f"{prefix}: {name}", getattr(module, name)) for name in names]


try:
    import _direct8_effects

    _direct8_effects.set_display(display, dual_layer)
    _direct8_effects.set_scroll_arrays(
        direct16_effects.x_scroll, direct16_effects.y_scroll
    )
    drawfuncs.extend(
        get_drawfuncs(
            _direct8_effects,
            "native",
            ["palcycle", "simplexor", "xor_scroll", "plasma_scroll", "random_noise"],
        )
    )

    from _direct8_effects import overlay
except ImportError:

    @micropython.viper
    def overlay(t: uint):
        fb = ptr16(display)

        for idx in range(240 * 32):
            fb[idx] >>= 1
            fb[idx] &= 0b01111_011111_01111


drawfuncs.extend([("viper: palcycle", palcycle), ("viper: simple_xor", simple_xor)])


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
                display.direct8_prepare(1)
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
        display.direct8_prepare(0)
        lock.acquire()
        overlay(t[SHARED_TICK])
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


def palette_cycle_direct():
    # Only time we touch the pixel data
    fill8(0)

    draw_duration = 0
    present_duration = 0
    tick = 0
    new_palette = array("H", [direct16_effects.palette[tick]])
    while True:
        start = ticks_us()
        new_palette[0] = direct16_effects.palette[tick & 0xFF]
        display.direct8_palette(new_palette)
        draw_duration += ticks_us() - start
        draw_duration >>= 1

        tick += 1

        start = ticks_us()
        update()
        present_duration += ticks_us() - start
        present_duration >>= 1

        if tick & 31 == 0:
            if draw_duration > 0:
                print(f"avg draw: {draw_duration:<10} avg present: {present_duration}")
            gc.collect()


if dual_layer:
    # Only run this once to demonstrate non-destructive update
    simple_xor(0, 0)
    simple_xor(0, HALF_HEIGHT)
    fill8_upper(0)
    # main([("l1 checker", layer1_checker_scroll)])
    main([("l1 plasma", _direct8_effects.l1_plasma_scroll)])
# palette_cycle_direct()

# main(get_drawfuncs(_direct8_effects, "native", ["xor_scroll", "plasma_scroll"]))
main(drawfuncs)
