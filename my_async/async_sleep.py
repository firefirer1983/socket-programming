import asyncio
import time

show = lambda: print(time.time())


async def slow_get(x):
    print('%u slow get' % x)
    await asyncio.sleep(x)
    print('slow get done')

show()
f1 = asyncio.ensure_future(slow_get(1))
f2 = asyncio.ensure_future(slow_get(2))
f3 = asyncio.ensure_future(slow_get(3))
show()
loop = asyncio.get_event_loop()
show()
loop.run_until_complete(asyncio.wait([f1, f2, f3]))
show()


