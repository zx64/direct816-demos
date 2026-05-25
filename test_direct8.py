# TODO
# Merge common logic with test_direct16
# Dual layer support for drawfuncs
import gc
import micropython
import direct8_effects
from array import array
from common_effects import generate_palette, make_palette_cycle, x_scroll, y_scroll
from common_effects import orange_cycle as palette
from time import ticks_us

update = display.update
dual_layer = const(0)
use_pio = const(0)
use_prepare = const(1)
use_overlay = const(0)
if use_pio:
    assert hasattr(display, "direct8_pio")
assert (
    (use_pio and not dual_layer)
    or (dual_layer and not use_pio)
    or (not dual_layer and not use_pio)
)
display.direct8(True, dual_layer)  # requires changes made locally
if use_pio:
    display.direct8_pio(use_pio)
display.direct8_palette(palette, 0)
if dual_layer:
    l1_palette = make_palette_cycle(generate_palette(lambda i: (i // 8, i, i // 4)))
    display.direct8_palette(l1_palette, 1)

# display.set_vsync(False)
WIDTH = const(240)
HEIGHT = const(320)
HALF_HEIGHT = const(HEIGHT // 2)
SIZE = const(WIDTH * HEIGHT)
effect_duration = const(511)
assert len(memoryview(display)) == 2 * SIZE if dual_layer else SIZE


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
    _direct8_effects.set_scroll_arrays(x_scroll, y_scroll)
    drawfuncs.extend(
        get_drawfuncs(
            _direct8_effects,
            "native",
            ["palcycle", "simplexor", "xor_scroll", "plasma_scroll", "random_noise"],
        )
    )

except ImportError:
    pass

if use_pio or not use_prepare:

    def overlay(t):
        pass

    def prepare(t):
        return 0
else:
    prepare = display.direct8_prepare

    if not use_overlay:

        def overlay(t):
            pass
    else:
        try:
            import _direct8_effects
            from _direct8_effects import overlay
        except ImportError:

            @micropython.viper
            def overlay(t: uint):
                fb = ptr16(display)

                for idx in range(240 * 32):
                    fb[idx] >>= 1
                    fb[idx] &= 0b01111_011111_01111


drawfuncs.extend(get_drawfuncs(direct8_effects, "viper", ["palcycle", "simple_xor"]))


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
                prepare(1)
            lock.release()

    df_name, drawfunc = drawfuncs[t[SHARED_DRAWIDX]]
    print(f"{df_name}")
    draw_duration = 0
    present_wait_duration = 0
    present_duration = 0
    prepare_blit = 0
    prepare_dma_wait = 0
    _thread.start_new_thread(threadfunc, (t,))
    done = False

    while True:
        start = ticks_us()
        drawfunc(t[SHARED_TICK], 0)
        prep_start = ticks_us()
        dma_wait = prepare(0)
        prepare_blit += ticks_us() - prep_start - dma_wait
        prepare_blit >>= 1
        prepare_dma_wait += dma_wait
        prepare_dma_wait >>= 1
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
        present_wait = update()
        present_wait_duration += present_wait
        present_wait_duration >>= 1
        present_duration += ticks_us() - start - present_wait
        present_duration >>= 1

        if t[SHARED_TICK] & effect_duration == 0:
            new_idx = t[SHARED_DRAWIDX] = (t[SHARED_DRAWIDX] + 1) % len(drawfuncs)
            df_name, drawfunc = drawfuncs[new_idx]
            draw_only = draw_duration - prepare_blit - prepare_dma_wait
            print(
                f"draw: {draw_only:<10} prepare: {prepare_blit:<10} dma stall: {prepare_dma_wait:<10} vsync: {present_wait_duration:<10} present: {present_duration}"
            )
            print(f"{df_name}")
            draw_duration = 0
            prepare_blit = 0
            present_duration = 0
            prepare_dma_wait = 0

        lock.release()
        if t[SHARED_TICK] & 31 == 0:
            if draw_duration > 0:
                draw_only = draw_duration - prepare_blit - prepare_dma_wait
                print(
                    f"draw: {draw_only:<10} prepare: {prepare_blit:<10} dma stall: {prepare_dma_wait:<10} vsync: {present_wait_duration:<10} present: {present_duration}"
                )
            gc.collect()


def palette_cycle_direct():
    # Only time we touch the pixel data
    fill8(0)

    draw_duration = 0
    present_duration = 0
    tick = 0
    new_palette = array("H", [palette[tick]])
    while True:
        start = ticks_us()
        new_palette[0] = palette[tick & 0xFF]
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


if __name__ == "__main__":
    if dual_layer:
        # Only run this once to demonstrate non-destructive update
        simple_xor(0, 0)
        simple_xor(0, HALF_HEIGHT)
        fill8_upper(0)
        # main([("l1 checker", layer1_checker_scroll)])
        main([("l1 plasma", _direct8_effects.l1_plasma_scroll)])
        # palette_cycle_direct()
    else:
        # main(get_drawfuncs(_direct8_effects, "native", ["xor_scroll", "plasma_scroll"]))
        main(drawfuncs)
