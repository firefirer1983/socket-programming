import functools
import time
import asyncio

now = lambda: time.time()


def cb(f):
    print('cb:', f)
    print('future result:', f.result())


async def test_co():
    return 'finished'


co = test_co()

loop = asyncio.get_event_loop()

f = asyncio.ensure_future(co)
f.add_done_callback(cb)
loop.run_until_complete(f)


def cb2(x, f):
    print('future:', f, 'result:', f.result(), 'x:', x)


co2 = test_co()
f2 = asyncio.ensure_future(co2)
f2.add_done_callback(functools.partial(cb2, 5))
loop.run_until_complete(f2)
print('result:', f.result(), f2.result())
