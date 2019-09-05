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

http_req = """GET %s HTTP/1.1\r\n
Host: %s\r\n
User-Agent: Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36
(KHTML, like Gecko) Chrome/44.0.2403.125 Safari/537.36\r\n
Accept: */*\r\n\r\n"""


def http_get(host, path):
    return http_req % (path, host)


google_rsp = """
<HTML><HEAD><meta http-equiv="content-type" content="text/html;charset=utf-8">
<TITLE>301 Moved</TITLE></HEAD><BODY>
<H1>301 Moved</H1>
The document has moved
<A HREF="http://www.google.com/">here</A>.
</BODY></HTML>
"""


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
        print("start send address request")
        await loop.sock_sendall(sock, addr_req)
        print("start send address request done")
        addr_rsp = await async_pull(Socks5AddrRspGen(), loop, sock)
        print(addr_rsp)
        req = http_get("google.com", "/")
        print(req)
        await loop.sock_sendall(sock, req.encode("utf8"))
        html = await loop.sock_recv(sock, 4096)
        print("html:", html.decode("utf8"))


if __name__ == "__main__":
    mloop = asyncio.get_event_loop()
    mloop.run_until_complete(client(mloop))
