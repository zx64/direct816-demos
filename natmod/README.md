Note: Native modules only build with `make`, which isn't as straightforward on Windows
compared to normal Pico SDK projects.

Tested with [ARM GCC 15.2](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)

MicroPython documentation about [native modules](https://docs.micropython.org/en/latest/develop/natmod.html)

- Clone or symlink my [branch of MicroPython](https://github.com/zx64/micropython/tree/bw-1.28.0) to this directory as `micropython`
- `make -C direct16 && make -C direct8`
    - TODO: Top level makefile
- `mpremote cp direct16/_direct16_effects.mpy direct8/_direct8_effects.mpy :`
    - TODO: Add deploy target to top level Makefile

