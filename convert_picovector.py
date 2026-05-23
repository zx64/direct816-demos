from array import array

# PicoVector coordinates, assuming pixel double mode
HALF_PV_WIDTH = const(160)
HALF_PV_HEIGHT = const(120)

# Direct coordinates, note x and y are swapped!
FRAME_WIDTH = const(240)
FRAME_HEIGHT = const(320)


# TODO: This version uses 150K of temporary storage, but you can use less:
# https://en.wikipedia.org/wiki/In-place_matrix_transposition
@micropython.viper
def _copyconv(temp_output):
    rgb888 = ptr32(display)
    tmp = ptr16(temp_output)

    for pv_x in range(HALF_PV_WIDTH):
        for pv_y in range(HALF_PV_HEIGHT):
            old_pos = pv_y * HALF_PV_WIDTH + pv_x
            src = uint(rgb888[old_pos])

            p16: uint = (
                (src & 0xF8) << 8 | (src & 0xFC00) >> 5 | (src & 0xF8_00_00) >> 19
            )
            new_pos = pv_x * HALF_PV_HEIGHT + pv_y
            tmp[new_pos] = p16

    rgb565 = ptr16(display)
    for y in range(FRAME_HEIGHT // 2):
        for x in range(FRAME_WIDTH // 2):
            p = tmp[y * (FRAME_WIDTH // 2) + x]

            rgb565[(2 * y) * FRAME_WIDTH + 2 * x] = p
            rgb565[(2 * y) * FRAME_WIDTH + 2 * x + 1] = p
            rgb565[(2 * y + 1) * FRAME_WIDTH + 2 * x] = p
            rgb565[(2 * y + 1) * FRAME_WIDTH + 2 * x + 1] = p


def copyconv_pixdbl():
    temp_output = array("H", [0] * HALF_PV_WIDTH * HALF_PV_HEIGHT)
    _copyconv(temp_output)


badge.mode(LORES | VSYNC)
screen.pen = color.rgb(0, 0, 0, 255)
screen.clear()
screen.pen = color.rgb(255, 0, 0, 255)
screen.rectangle(5, 5, 133, 100)
screen.pen = color.rgb(0, 255, 0, 255)
screen.rectangle(10, 10, 133, 100)
screen.pen = color.rgb(0, 0, 255, 255)
screen.rectangle(15, 15, 133, 100)
screen.pen = color.rgb(255, 0, 0, 255)
copyconv_pixdbl()
display.direct16(True)
display.update()
