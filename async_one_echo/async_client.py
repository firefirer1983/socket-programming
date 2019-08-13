import socket
import asyncio


loop = asyncio.get_event_loop()


async def client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        s.setblocking(False)
        await loop.sock_connect(s, ('127.0.0.1', 5566))
        received = b'hello world'
        while True:
            await loop.sock_sendall(s, received)
            received = await loop.sock_recv(s, 1024)
            print('received:', received)
            if not received:
                break
            
loop.create_task(client())
loop.run_forever()


