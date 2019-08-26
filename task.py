# !/usr/bin/env python3

import functools
from concurrent.futures import ThreadPoolExecutor
from time import sleep


pool = ThreadPoolExecutor(max_workers=8)


class Task:
    
    def __init__(self, gen):
        self._gen = gen
        
    def step(self, value=None):
        try:
            fut_ = self._gen.send(value)
            fut_.add_done_callback(self.wakeup)
        except StopIteration:
            pass

    def wakeup(self, fut):
        self.step(fut.result())


def coroutine(f):
    @functools.wraps(f)
    def _func(*args, **kwargs):
        result = yield pool.submit(f, *args, **kwargs)
        print("result:", result)
    return _func


def multiply(x, y):
    sleep(5)
    return x * y


def func_wrapper(x, y):
    value = yield pool.submit(multiply, x, y)
    print("value:", value)


@coroutine
def add(x, y):
    sleep(5)
    return x + y


m = Task(func_wrapper(5, 6))
a = Task(add(1, 1))
m.step(None)
a.step(None)
print("step")
