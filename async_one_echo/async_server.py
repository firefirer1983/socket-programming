import socket
import asyncio


loop = asyncio.get_event_loop()


async def sock_handler(sock):
    while True:
        received = await loop.sock_recv(sock, 1024)
        print('received:', received)
        if not received:
            sock.close()
        await loop.sock_sendall(sock, received)
        print('sendall')


async def server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        s.setblocking(False)
        s.bind(('127.0.0.1', 5566))
        s.listen(socket.SOMAXCONN)
        while True:
            csock, address = await loop.sock_accept(s)
            print('connect from :', address)
            loop.create_task(sock_handler(csock))
            print('1 loop done')
    
loop.create_task(server())
loop.run_forever()
