import asyncio


mloop = asyncio.get_event_loop()


class Authorizer:
    def __init__(self, loop):
        self._loop = loop

    async def authorize(self):
        print("start authorizing")
        ret = await self.background_check()
        print("authorized done")
        return ret

    async def background_check(self):
        print("start back group checking")
        await asyncio.sleep(5)
        print("back group check done")
        return "OK"


class Relay:
    def __init__(self, loop):
        self._loop = loop

    async def relay(self):
        print("start relaying")
        await asyncio.sleep(5)
        print("relay done!")
        return "OK"


async def main():

    authority = Authorizer(mloop)
    auth_res = await authority.authorize()
    print("auth:", auth_res)
    relayer = Relay(mloop)
    while True:
        relay_res = await relayer.relay()
        print("relay:", relay_res)


if __name__ == "__main__":
    mloop.run_until_complete(main())
