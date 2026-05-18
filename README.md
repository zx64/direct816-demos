# direct816-demos
Tests for my [Direct816 branch of Tufty2350](https://github.com/zx64/tufty2350)

My version of Tufty2350 and the native modules here are built against my [branch of MicroPython](https://github.com/zx64/micropython/tree/bw-1.28.0) that has rebased the [Pimoroni bw-1.27.0](https://github.com/pimoroni/micropython/tree/bw-1.27.0) changes on top of [MicroPython 1.28](https://github.com/micropython/micropython/releases/tag/v1.28.0).

Tested with [ARM GCC 15.2](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)


# Direct816?
The [existing graphics APIs](https://badgewa.re/docs) included in the Tufty2350 firmware
are very approachable and have other benefits like easy porting between the other badges,
[a simulator](http://github.com/pimoroni/badgeware-simulator) and even runnable examples
inside the documentation using a WASM port.

The existing driver converts from 32-bit RGB888 landscape to 16-bit RGB565 portrait every
update, which is great if you don't want to care about handling that but you can get
increased performance if you're willing to deal with these steps yourself.

While the ST7789 is able to rotate pixel data given to it, it is unable to do so without
introducing an ugly diagonal tear line, even if you are perfectly syncing with its vsync
signal.

My branch adds two modes to the ST7789 driver: Direct 8 and Direct 16.

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

The layer merging and RGB565 conversion is performed before waiting for vertical sync, so
it's effectively free if you finish frames fast enough.

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


# Multicore support
I have re-enabled the [`_thread` module](https://docs.micropython.org/en/latest/library/_thread.html) which allows for the second core to assist with drawing from MicroPython.
This along with [MicroPython's Viper code generator](https://docs.micropython.org/en/latest/reference/speed_python.html#the-viper-code-emitter) has allowed me to make effects in pure Python that still run at 60FPS.

[Native modules](https://docs.micropython.org/en/latest/develop/natmod.html) are still faster but can be less convenient for prototyping.

The multi-threading in the demos isn't especially sophisticated: each core is given half
the framebuffer to draw from a shared tick. This avoids having to implement more complex
state sharing.

Theoretically the Direct8 conversion could also be assisted by the second core but since
that code is pure C++, it would need more complex code to share with MicroPython.

# TODO
- Improve implementation
- New effects
- UI
- Package into a Badgeware app. For now I'm just copying libraries and launching with
  `mpremote run`
