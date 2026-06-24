Note: Native modules only build with `make`, which isn't as straightforward on Windows
compared to normal Pico SDK projects.

Tested with [ARM GCC 15.2](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)

MicroPython documentation about [native modules](https://docs.micropython.org/en/latest/develop/natmod.html)

- Clone or symlink my [branch of MicroPython](https://github.com/zx64/micropython/tree/bw-1.28.0) to this directory as `micropython`
- `make`
The modules are intended to be bundled with the apps (TODO: extract from CI script), but
if you want to use them with `mpremote run` etc. then:
 - You'll need to run `mpremote mkdir :/lib` if it's not there.
- `make deploy` (copies all native modules to the newly created directory)
