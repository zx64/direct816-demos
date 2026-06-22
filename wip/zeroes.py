import array
import gc
import micropython
import time


def benchmark(name, func, n):
    memsnapshot = [0, 0, 0]
    expected_use = n * 2
    print(f"-----------------\n            {name}")
    gc.collect()
    memsnapshot[0] = gc.mem_alloc()
    print("running...", end="\r")
    start = time.ticks_us()
    r = func(n)
    duration = time.ticks_diff(time.ticks_us(), start) / 1000
    print(f"duration: {duration:.2f}ms ({1000 * duration / n:.2f}us per n)")
    memsnapshot[1] = gc.mem_alloc()
    gc.collect()
    memsnapshot[2] = gc.mem_alloc()
    print(f"temp allocations: {memsnapshot[1] - memsnapshot[2]} bytes")
    print(f"final overhead: {memsnapshot[2] - memsnapshot[0] - expected_use} bytes")
    return r


@micropython.viper
def test_bytearray(n: uint):
    """Test allocating with bytearray"""
    return array.array("H", bytearray(n * 2))


@micropython.viper
def test_bytearray_only(n: uint):
    """Test only allocating the bytearray, assumes you'll use ptr16 later"""
    return bytearray(n * 2)


@micropython.viper
def test_bytes(n: uint):
    """Test allocating with bytes"""
    return array.array("H", bytes(n * 2))


class CustomIterator:
    def __init__(self, n):
        self.n = n

    # Comment out this function to make it perform as badly as the generator versions
    def __len__(self):
        return self.n

    def __iter__(self):
        for _ in range(self.n):
            yield 0


@micropython.viper
def test_custom_iterator(n: uint):
    """Custom iterator that provides a __len__ method."""
    return array.array("H", CustomIterator(n))


# Using viper on this function works on device but trips an assert in mpy-cross:
# Assertion failed: vtype_item == VTYPE_PYOBJ, file micropython/py/emitnative.c, line 2725
# I think it's because that code assumes the list comprehension variable gets used
@micropython.viper
def test_list_comprehension(n: uint):
    """Using a list comprehension"""
    return array.array("H", [0 for _ in range(n)])


@micropython.viper
def test_range_nonzero(n: uint):
    """Use a native range directly, doesn't zero init but might still be useful"""
    return array.array("H", range(n))


def make_zero_list(n):
    # Viper doesn't support this operation, so we extract it from the test function
    return [0] * n


@micropython.viper
def test_zero_list(n: uint):
    """Existing implementation where a list is grown to size before handing off to array"""
    return array.array("H", make_zero_list(n))


# These versions are very slow, presumably because no length information is available
# Viper also does not support yield
def zero_generator(n):
    for _ in range(n):
        yield 0


@micropython.viper
def test_zzz_generator_function(n: uint):
    """Simple generator"""
    return array.array("H", zero_generator(n))


# Viper does not support yield
def test_zzz_generator_expression(n):
    """Using a generator expression"""
    return array.array("H", (0 for _ in range(n)))


fbsize = const(320 * 240 * 2)
for name, func in sorted(
    (name, func) for (name, func) in globals().items() if name.startswith("test_")
):
    arr = benchmark(name, func, fbsize)
