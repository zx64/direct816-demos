# direct816-demos
Tests for my [Direct816 branch of Tufty2350](https://github.com/zx64/tufty2350)

My version of Tufty2350 and the native modules here are built against my [branch of MicroPython](https://github.com/zx64/micropython/tree/bw-1.28.0) that has rebased the [Pimoroni bw-1.27.0](https://github.com/pimoroni/micropython/tree/bw-1.27.0) changes on top of [MicroPython 1.28](https://github.com/micropython/micropython/releases/tag/v1.28.0).

Tested with [ARM GCC 15.2](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)

I wouldn't call the following documentation yet, it's mostly a braindump of "Oh I should
mention that" while I think through the scope and API for this.

No AI was used during any step of this.

# Direct816?
The [existing graphics APIs](https://badgewa.re/docs) included in the Tufty2350 firmware
are very approachable and have other benefits like easy porting between the other badges,
[a simulator](http://github.com/pimoroni/badgeware-simulator) and even runnable examples
inside the documentation using a [WASM port](https://github.com/pimoroni/badgeware-web/).

The existing driver converts from 32-bit RGB888 landscape to 16-bit RGB565 portrait every
update, which makes it easier to focus on getting cool stuff on screen but you can get
increased performance if you're willing to handle the extra complexity.

While the ST7789 is able to rotate pixel data given to it, it is unable to do so without
introducing an ugly diagonal tear line, even if you are perfectly syncing with its vsync
signal.

My branch adds two modes to the ST7789 driver: Direct 8 and Direct 16.

(Direct8 grew out of me using palettes to simplify my testing of Direct16 and figured I
might as well implement an 8-bit mode as a convenience feature in the driver)

## Direct16
Enable with `display.direct16(True)`

Direct16 is the simplest: draw to the 240x320 RGB565 framebuffer provided, call
`display.update()`.

Important: the address of the framebuffer changes with every update, so you have to redraw
the entire frame every frame.

In addition to skipping conversion steps, this mode is able to use half of the memory
previously needed for the RGB888 framebuffer to implement double buffering with DMA.
This means your code can start drawing even while the LCD is refreshing without
introducing any tearing.

Your drawing code also gets a speedup from only having to write two bytes per pixel
instead of four. You can write two pixels at a time by performing 32-bit writes which can
accelerate fills and vertical lines. (Remember that the framebuffer is considered portrait)

## Direct8
Direct8 is an 8-bit indexed mode with optional dual layer support.

The second layer has its own independently settable palette, with index 0 being treated as
transparent.

Enable with `display.direct8(True, False)` for single layer and `display.direct8(True,
True)` for dual layer.

Palettes are copied in with `display.direct8_palette(palette, layer)` where the layer
number can be `0` or `1` to only update that layer's palette or `-1` to update both with
the same palette. See below for more details on palettes.

Since Direct8 uses a quarter of the memory previously allocated for an RGB888 framebuffer,
we have room for two 8-bit layers as well as room for converting the result to RGB565.

Again, by having separate input and output buffers, your code can resume drawing almost
immediately after vertical sync.

Unlike Direct16, the framebuffers you access remain in the same place and are not touched
by the display driver. This allows you to perform partial drawing as well as palette
cycling with minimal overhead.

Since each pixel is now only one byte, you get further speedups when drawing. Fills and
vertical lines can be done four pixels at a time with 32-bit writes.

### Palettes
The simplest palette you can provide is `array.array("H", [0])`.

The API copies the palette provided into its own memory, so while you can change the
palette every frame, you have to call `display.direct8_palette` to see the changes.

You can have up to 256 palette entries in RGB565 format.

Currently the API writes the provided palette to the start and then fills the remaining
entries with black.

Further features could include specifying the range to update or having the native code
rotate a subset.

### Frame Preparation
By default, the driver will perform the layer merging and colour conversion inside
`display.update()` during time usually spent waiting for vertical sync.

However, if your frame generation gets especially complex, the cost of this operation will
become apparent.

The user code can explicitly invoke `display.direct8_prepare(-1)` once the indexed drawing
operations have completed, giving an opportunity to perform post-processing outside of the
existing palettes.

Additionally, the work can be shared between the two cores with a parameter indicating if
this is being run from the second core or not.

### One layer or two?
Adding a second layer adds more overhead than just implementing layering in one layer, but
it has some unique features that might be a good tradeoff:

You can have separate palettes for the two layers, which allows for higher quality
backgrounds and layer specific palette cycling effects.

Layers do not have to be fully redrawn every frame in Direct8.
If you have a static background, you can draw that once and then your sprite drawing code
for the second layer only has to clear to zero to undraw a pixel rather than having to
sample from the background.
A static background can still be animated with palette cycling.

# Multicore support
I have re-enabled the [`_thread` module](https://docs.micropython.org/en/latest/library/_thread.html) which allows for the second core to assist with drawing from MicroPython.
This along with [MicroPython's Viper code generator](https://docs.micropython.org/en/latest/reference/speed_python.html#the-viper-code-emitter) has allowed me to make effects in pure Python that still run at 60FPS.

[Further Viper documentation](https://github.com/micropython/micropython/wiki/Improving-performance-with-Viper-code)

[Native modules](https://docs.micropython.org/en/latest/develop/natmod.html) are even faster but can be less convenient for prototyping.

The multi-threading in the demos isn't especially sophisticated: each core is given half
the framebuffer to draw from a shared tick. This avoids having to implement more complex
state sharing.

Direct8's conversion to RGB565 can be shared between the two cores, but requires the user
code to coordinate scheduling and synchronisation.


# 16-bit DMA for pixels
The branch also fixes needing to perform endian conversion by the CPU for every pixel,
even in the original modes.

By reconfiguring the DMA and PIO to use 16-bit transfers for pixel data, we avoid needing
to perform any endian swapping.

I had originally thought I'd need to use
[`channel_config_set_bswap`](https://www.raspberrypi.com/documentation/pico-sdk/hardware.html#group_channel_config)
to swap endianness during the transfer, however simply adjusting the transfer width and
the PIO code accomplished the desired outcome.

# TODO
## For [the branch](https://github.com/zx64/tufty2350):
- Start tagging versions to be handled as releases by GitHub for easier downloading
- Update the ci/micropython.sh script to fetch the latest version of the (eventual) app
  from this repository so it can be included in the `tufty-with-filesystem.uf2` releases.
- Investigate adapting existing drawing libraries like PicoGraphics and PicoVector
    - PicoVector might just need some custom brush and colour classes to output in the
      right format and coordinates.
    - Critical problem is Direct16 alternates between halves of the framebuffer which
      PicoVector is unaware of.
    - A less intrusive change could be only using PicoVector to draw to offscreen
      textures. This would still benefit from having native transposed drawing and RGB565
      conversion.
    - Offline conversion would be better for load times but it is a nicer developer
      experience to more easily port over bits of your drawing code.
- Investigate what can be accelerated with the interpolator hardware
- Extract common helper functions from the demos into new module(s)
  - See later for more thoughts on this

### Direct8 specific:
- More palette operations: write to subset, rotate inside subset
    - Maybe implement buffer protocol for palettes?
       - Need to wait for DMA before the palette can be safely written
    - Fades to white/black would be convenient but can be precalculated
- Palette conversion can be performed inside the DMA transfer to the display with the help
  of some PIO tricks, which avoids needing to write back to memory.
    - This gets a lot more complex once layers enter the picture
    - In progress on another branch, but inital results seem close to doing this work on
      the CPU and thus a less exciting prospect than when I first got it working on the
      original Tufty2040.

## For this repository and the demos:
- CI doesn't mark a commit as bad even if the interior build task fails
- Tidy up code duplication between the two testbeds
- Document how I'm using `_thread`
  - The current approach uses a single lock to ensure either core 0 and 1 are drawing XOR
    core 0 is updating shared state, waiting for vsync and issuing DMA.
  - Should be replaced by the design outlined later on.
- Add a way for two layer effects to be specified
  - Should be handled by the design outlined later on.
- Add an optional state update function to effects that happens before drawing
  - Should be handled by the design outlined later on.
- Use Tufty2350's buttons to cycle through effects
- Add a menu for effects like the [existing effects demo](https://github.com/pimoroni/tufty2350/tree/main/firmware/apps/demos)
- Add way to switch between palettes
- Add title cards for each effect
- New effects
    - I'd like to implement various 80s-90s demo effects
    - Remake the [world demo](https://github.com/pimoroni/tufty2350/tree/main/firmware/apps/demos/demos/world.py)
    - [ST-NICCC](https://www.pouet.net/prod.php?which=1251) is a classic precalculated
      polygon animation that has been ported to a lot of platforms. Not quite at the same
      level as Bad Apple or Doom but either way, should look great on Tufty's display.
- Preview screenshots and videos
- Tools to prepare images and palettes
- Make boot button exit to bootloader
  - Badgeware already registers an IRQ for that button to reset
  - Alternative: add the picotool Reset handler to MicroPython

# More rambling that I felt needed writing down somewhere
There is potential for some further improvements with more intrusive changes to the ST7789
driver to take into account the specifics of the RP2350 bus fabric (section 2.1 of the
RP2350 datasheet), for example the framebuffers could be stored in separate parts of SRAM
so the two cores and DMA are less likely to conflict.

I'm ruling that out of scope as I want these changes to exist alongside the existing
firmware.

A fully native program will have less overhead, but I'm pleasantly surprised by what you
can get out of MicroPython and its simplicity helps with the code outside of the critical
path.

I'd like to eventually change how MicroPython native modules are built so it's less clunky
on Windows, supports C++ and can use some Pico SDK features. But I already have plenty on
that list above so unlikely to happen.

Linus Akesson's post about his 2025 demo [Kaleidoscopico](https://www.linusakesson.net/scene/kaleidoscopico/index.php) is great reading and talks about his 12-bit palette implementation.

He is also working on a technical video about his 2026 demo [Sum Ergo Demonstro](https://linusakesson.net/scene/sum-ergo-demonstro/index.php).


# Thoughts on how to refactor the demo code into a better app
Effects get refactored into something like
```python
class Effect:
    name: str

    def handle_input(self, t: int, dT: float):
        pass

    def update(self, t: int, dT: float, core1: bool):
        pass

    def draw(self, dest: rect, core1: bool):
        pass
```

The app logic is implemented as a multi-threaded state machine, where core 1 waits at the
line for core 0 before proceeding to the next step.

```
State #                    Core 0    Core 1
-----------------------------------------------------
0                   global_input()   ---- IDLE ----
           tick++, dT = now - prev
-----------------------------------------------------
1                    select next effect(s)
-----------------------------------------------------
2        effect_input[n](tick, dT)   ---- IDLE ----
-----------------------------------------------------
3  update_overlay(tick, dT, False)   update_overlay(tick, dT, True)
        update[n](tick, dT, False)   update[n](tick, dT, True)
-----------------------------------------------------
4       draw[n](dest[n][0], False)   draw[n](dest[n][1], True)
                    prepare(False)   prepare(True)
                    overlay(False)   overlay(True)
-----------------------------------------------------
5                        present()   ---- IDLE ----
-----------------------------------------------------
```

## Locks and thread safety
The only locking implemented is related to advancing the state machine.

Effects should be written to avoid needing any finer grained locks, e.g.
- Update: Identify and partition independent calculations
- Draw: Do not update shared state
- Draw: only writing to the region of pixels provided by the framework, which ensures
  disjoint regions between the two cores.

As a last resort, effects can create their own lock object with `_thread.allocate_lock()`
in their `__init__` and use `with` blocks to guard critical sections.

## State 0
`global_input` handles menu actions to change effect and palette as well as time keeping

## State 1
Each thread's function pointers for the subsequent states are updated according to
decisions made in state 0.

## State 2
`effect_input` usually a no-op but could be used to read sensor stick or poll controller

## State 3
`update_overlay` steps any animations related to the overlay as well as any effect
transition

`update` allows for per-frame calculations and state mutations that are guaranteed to
complete before any drawing.

Multi-threading this may be difficult because of data dependencies between sophisticated
calculations, but simple particle logic like `position[n] += velocity[n] * dT` over two
non-overlapping ranges should be fine.

## State 4
Effects should not mutate any shared state during this phase to ensure everything should
be safe to read from either core.

### draw
`draw` isn't necessarily updating the entire screen (or half screen), there are various
transitions between effects that can be accomplished by animating the destination
rectangles inside `update_overlay`. e.g. slide in from one side, grow outwards from a point

Another use for sub-screen drawing would be live previews of the effects on a menu

Caution: the provided destination rectangle is different on either core, only ever draw
inside the rectangle provided

### prepare
`prepare` is a no-op in direct16 mode, no point in waiting for DMA to finish yet

### overlay
`overlay` is where the menu and any other light UI elements are drawn, always as direct16

Important: do as little as possible to leave as much time for effect drawing

## State 5
`present` will wait for DMA (direct16 only) and vsync (both) before initiating a new DMA
transfer for the new framebuffer.


# Direct816 blitter API

The conversion and blitting code currently living in `direct16_effects.py` should be
extracted into a more reusable API, something conceptually like this but using as much
native code as possible.

```python
Mask16Skip = const(0) # blit all pixels (small optimisation for background blits)
Mask16Transparent = const(1) # unmasked pixels are not written
Mask16Darken = const(2) # unmasked pixels are darkened by halving their value

class D16Image:
    w: int
    h: int
    pixels: array("H")
    mask: array("B") | None

    def blit(self, src: rect, dest: rect, masked: int):
        pass

Mask8Skip = const(0) # blit all pixels
Mask8Use = const(1) # use mask array or palette index
Mask8Threshold = const(2) # any palette index less than this value is skipped

class D8Image:
    w: int
    h: int
    pixels: array("B")
    mask: array("B") | int

    def blit(self, src: rect, dest: rect, masked: int):
        pass

```
