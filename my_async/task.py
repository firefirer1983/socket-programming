# !/usr/bin/env python3

import functools
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import Future

pool = ThreadPoolExecutor(max_workers=8)


def __iter__(self: Future):
    if not self.done():
        yield self
    else:
        return self.result()


Future.__iter__ = __iter__


class Task(Future):
    def __init__(self, gen):
        super().__init__()
        self._gen = gen
    
    def step(self, value=None):
        try:
            fut_ = self._gen.send(value)
            fut_.add_done_callback(self.wakeup)
        except StopIteration as e:
            self.set_result(e.value)
    
    def wakeup(self, fut):
        try:
            self.step(fut.result())
        except Exception as e:
            fut.throw(e)


def co_routine(f):
    @functools.wraps(f)
    def _func(*args, **kwargs):
        result = yield pool.submit(f, *args, **kwargs)
        return result
    
    return _func


@co_routine
def add(x, y):
    time.sleep(2)
    return x + y


@co_routine
def multiply(x, y):
    time.sleep(2)
    return x * y


@co_routine
def subtract(x, y):
    return x - y


def after(delay, fut):
    yield from pool.submit(functools.partial(time.sleep, delay))
    ret = yield from fut
    return ret


if __name__ == "__main__":
    t = Task(add(1, 1))
    t.step()
    
    t_add = Task(after(2, add(5, 6)))
    print("start add")
    t_add.step()
    
    t_mul = Task(after(2, multiply(3, 4)))
    t_mul.step()
    print("start mul")
    
    t_sub = Task(after(2, subtract(8, 32)))
    t_sub.step()
    print("start sub")
    
    start = time.time()
    print(t_add.result(), t_mul.result(), t_sub.result())
    print("%r seconds elapsed" % (time.time() - start))

