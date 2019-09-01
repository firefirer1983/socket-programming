import asyncio
import socket

from sockets5.socks5_req import Socks5AuthRequest, Socks5AddrRequest
from sockets5.socks5_rsp import Socks5AddrRspGen, Socks5AuthRspGen
from utils.loggers import get_logger

from sockets5.enums import (
    Socks5AuthMethod,
    Socks5AddressAddrType,
    Socks5AddressCmd,
)
from utils.util import async_pull

log = get_logger("socks5-client")

HOST = "127.0.0.1"
PORT = 1081


async def client(loop):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        sock.setblocking(False)
        await loop.sock_connect(sock, (HOST, PORT))
        await loop.sock_sendall(
            sock, Socks5AuthRequest(Socks5AuthMethod.NO_AUTH)
        )
        auth_rsp = await async_pull(Socks5AuthRspGen(), loop, sock)
        log.info(f"auth_rsp: {auth_rsp}")
        addr_req = Socks5AddrRequest(
            Socks5AddressCmd.CONNECT,
            Socks5AddressAddrType.DOMAINNAME,
            b"google.com",
            80,
        ).to_bytes()
        await loop.sock_sendall(sock, addr_req)
        addr_rsp = await async_pull(Socks5AddrRspGen(), loop, sock)
        print(addr_rsp)
        await loop.sock_sendall(sock, b"try to connect")
        loop.stop()


if __name__ == "__main__":
    mloop = asyncio.get_event_loop()
    mloop.run_until_complete(client(mloop))
