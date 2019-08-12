import asyncio


async def test_co_routine():
    print('test async')

co = test_co_routine()
print(co, isinstance(co, asyncio.Future))
loop = asyncio.get_event_loop()
print('get event loop')
f = asyncio.ensure_future(co)
print(f, isinstance(f, asyncio.Future))
# t = loop.create_task(co)
# print(t, isinstance(t, asyncio.Future))

print('run until complete')
loop.run_until_complete(f)
