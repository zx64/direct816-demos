import _thread
import time
import random
from array import array


class Core1Runner:
    def __init__(self, functions):
        if not functions:
            raise ValueError("Must have at least one function")

        self.running = True
        self.lock = _thread.allocate_lock()
        self.phase = -1
        self.functions = functions

        def worker(self):
            last_phase = -1
            while True:
                with self.lock:
                    if not self.running:
                        return
                    new_phase = self.phase
                    f = self.functions[new_phase]

                if last_phase == new_phase:
                    time.sleep(0)
                    continue
                last_phase = new_phase
                f(True)

        _thread.start_new_thread(worker, (self,))

    def stop(self):
        with self.lock:
            self.running = False

    def next_phase(self):
        with self.lock:
            self.phase = (self.phase + 1) % len(self.functions)
        self.functions[self.phase](False)


class Counter(Core1Runner):
    def __init__(self):
        self.state1 = array("I", [0, 0])
        self.state2 = array("I", [0, 0])
        Core1Runner.__init__(self, [self.f1, self.f2])

    def f1(self, core1):
        self.state1[core1] += 1
        time.sleep_us(10 + random.randint(1, 4))

    def f2(self, core1):
        self.state2[core1] += 1
        time.sleep_us(11 + random.randint(1, 4))

    def result(self):
        print(self.state1, self.state2)


c1 = Counter()

for _ in range(10):
    c1.next_phase()

c1.stop()
c1.result()
