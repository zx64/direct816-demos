import array
import gc
import time


def benchmark(f):
    name = f.__name__[5:]

    def mf(n):
        memsnapshot = [0, 0, 0]
        expected_use = n * 2
        print(f"-----------------\n            {name}")
        gc.collect()
        memsnapshot[0] = gc.mem_alloc()
        print("running...", end="\r")
        start = time.ticks_us()
        r = f(n)
        duration = time.ticks_diff(time.ticks_us(), start) / 1000
        print(f"duration: {duration:.2f}ms ({1000 * duration / n:.2f}us per n)")
        memsnapshot[1] = gc.mem_alloc()
        gc.collect()
        memsnapshot[2] = gc.mem_alloc()
        print(f"temp allocations: {memsnapshot[1] - memsnapshot[2]} bytes")
        print(f"final overhead: {memsnapshot[2] - memsnapshot[0] - expected_use} bytes")
        return r

    return mf


@benchmark
def test_range_nonzero(n):
    """Use a native range (doesn't zero init)"""
    return array.array("H", range(n))


@benchmark
def test_grown_list(n):
    """Existing implementation where a list is grown to size before handing off to array"""

    def z(n):
        return [0] * n

    return array.array("H", z(n))


@benchmark
def test_bytearray(n):
    """Test allocating with bytearray"""
    return array.array("H", bytearray(n * 2))


@benchmark
def test_bytes(n):
    """Test allocating with bytes"""
    return array.array("H", bytes(n * 2))


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
for _, func in sorted(
    (name, func) for (name, func) in globals().items() if name.startswith("test_")
):
    arr = func(fbsize)
    assert len(arr) == fbsize
