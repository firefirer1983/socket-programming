import asyncio
import socket

from sockets5.enums import (
    Socks5AuthMethod,
    Socks5AddressAddrType,
)
from sockets5.socks5_req import Socks5AuthReqGen, Socks5AddrReqGen
from sockets5.socks5_rsp import Socks5AuthRsp, Socks5AddrRsp
from utils.util import async_pull

HOST = "127.0.0.1"
PORT = 1090


async def sock_handler(loop, sock):
    auth_req = await async_pull(Socks5AuthReqGen(), loop, sock)
    print("auth_req:", auth_req)
    await loop.sock_sendall(
        sock, Socks5AuthRsp(Socks5AuthMethod.NO_AUTH).to_bytes()
    )
    print("auth_rsp:", Socks5AuthRsp(Socks5AuthMethod.NO_AUTH).to_bytes())
    addr_req = await async_pull(Socks5AddrReqGen(), loop, sock)
    print("addr_req:", addr_req)
    rsp = Socks5AddrRsp(
        Socks5AddressAddrType.IP4, b"\x00.\x00.\x00.\x00", 5677
    )
    print("rsp: ", rsp)
    addr_rsp = rsp.to_bytes()
    print("addr rsp: %r" % addr_rsp)
    await loop.sock_sendall(sock, addr_rsp)
    
    if not auth_req:
        sock.close()
        return


async def server(loop):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        s.setblocking(False)
        s.bind((HOST, PORT))
        s.listen(socket.SOMAXCONN)
        while True:
            csock, address = await loop.sock_accept(s)
            print("connect from :", address)
            loop.create_task(sock_handler(loop, csock))


if __name__ == "__main__":

    mloop = asyncio.get_event_loop()
    mloop.run_until_complete(server(mloop))
