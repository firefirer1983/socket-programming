import socket

from sockets5.enums import Socks5AuthMethod, Socks5AddressAddrType
from sockets5.socks5_req import Socks5AuthReqGen, Socks5AddrReqGen
from sockets5.socks5_rsp import Socks5AuthRsp, Socks5AddrRsp
from utils.util import async_pull


class TCPRelay:
    def __init__(self, loop, is_sslocal, host, port):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setblocking(False)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self._sock.bind((host, port))
        self._sock.listen(socket.SOMAXCONN)
        self._loop = loop
        self._is_sslocal = is_sslocal
        self._host = host
        self._port = port

    async def accept(self):
        while True:
            csock, address = await self._loop.sock_accept(self._sock)

            print("connect from :", address)

            self._loop.create_task(
                TCPRelayHandler(self._loop, self._is_sslocal, csock).relay()
            )


class TCPRelayHandler:
    def __init__(self, loop, is_sslocal, sock):
        self._sock = sock
        self._remote_sock = None
        self._loop = loop
        self._is_sslocal = is_sslocal

    async def authorize(self):
        auth_req = await async_pull(Socks5AuthReqGen(), self._loop, self._sock)
        print("auth_req:", auth_req)
        await self._loop.sock_sendall(
            self._sock, Socks5AuthRsp(Socks5AuthMethod.NO_AUTH)
        )
        addr_req = await async_pull(Socks5AddrReqGen(), self._loop, self._sock)
        print("addr_req:", addr_req)
        await self._loop.sock_sendall(self._sock, Socks5AddrRsp(
            Socks5AddressAddrType.IP4, b"\x00.\x00.\x00.\x00", 5677
        ))
        return addr_req
        
    async def relay(self):
        res = await self.authorize()
        print("addr: %s port:%u" % (res.addr, res.port))
        if not res:
            return None
        await self.address(res.addr, res.port)
        self._loop.create_task(self.upstream())
        self._loop.create_task(self.downstream())
        
    async def address(self, addr, port):
        self._remote_sock = await self._loop.sock_connect((addr, port))
        self._loop.sock_sendall()
        
    async def upstream(self):
        while True:
            up_ = await self._loop.sock_recv(self._sock, 4096)
            await self._loop.sock_sendall(self._remote_sock, up_)
    
    async def downstream(self):
        while True:
            down_ = await self._remote_sock.sock_recv(self._remote_sock, 4096)
            await self._loop.sock_sendall(self._sock, down_)

        

