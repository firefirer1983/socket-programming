import asyncio
import contextlib
from functools import partial
from concurrent.futures import ThreadPoolExecutor

# pool = ThreadPoolExecutor()
#
#
# async def read_file(fpath, size):
#     with open(fpath, "r") as f:
#         txt = await asyncio.get_event_loop().run_in_executor(
#             pool, partial(f.read, size)
#         )
#         return txt
#
#
# # ret = loop.run_until_complete(read_file("/etc/passwd", 1024))
# ret = asyncio.run(read_file("/etc/passwd", 1024))


loop = asyncio.get_event_loop()


class SlowObj:
    def __init__(self, n):
        print("__init__")
        self._n = n

    def __await__(self):
        print("__await__ sleep({})".format(self._n))
        yield from asyncio.sleep(self._n)
        print("ok")
        return self


async def main():
    obj = await SlowObj(3)


loop.run_until_complete(main())
