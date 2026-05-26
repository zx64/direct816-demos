import direct16_effects

# Precache brush instances
pal = []
for i in range(256):
    screen.pen = direct16_effects.palette_hsv255[i]
    pal.append(screen.pen)

badge.mode(HIRES | VSYNC)
display.direct16(True)
for i in range(256):
    screen.pen = pal[i]
    screen.clear()
    screen.pen = pal[(i + 127) & 0xFF]
    screen.rectangle(25, 25, 100, 100)
    display.update()
