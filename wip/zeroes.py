import array
import gc
import micropython
import time


def benchmark(f):
    name = f.__name__[5:]

    def mf(n):
        print(f"              {name} start")
        gc.collect()
        micropython.mem_info()
        start = time.ticks_us()
        r = f(n)
        duration = time.ticks_diff(time.ticks_us(), start) / 1000
        print(f"              {name} {duration=:.2f}ms")
        gc.collect()
        micropython.mem_info()
        print("-----------------")
        return r

    return mf


@benchmark
def test_baseline(n):
    """Baseline using a native range (doesn't zero init)"""
    return array.array("H", range(n))


@benchmark
def test_existing(n):
    """Existing implementation where a list is grown to size before handing off to array"""

    def z(n):
        return [0] * n

    return array.array("H", z(n))


@benchmark
def test_bytearray(n):
    """Test allocating with bytearray"""
    return array.array("H", bytearray(n * 2))


@benchmark
def test_custom_iterator(n):
    """Custom iterator that provides a len method"""

    class z:
        def __init__(self, n):
            self.n = n

        def __len__(self):
            return self.n

        def __iter__(self):
            for _ in range(self.n):
                yield 0

    return array.array("H", z(n))


@benchmark
def test_generator_function(n):
    """Simple generator"""

    def z(n):
        for _ in range(n):
            yield 0

    return array.array("H", z(n))


fbsize = const(320 * 240 * 2)
for f in (v for k, v in globals().items() if k.startswith("test_")):
    arr = f(fbsize)
    assert len(arr) == fbsize
