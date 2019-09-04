import asyncio
import socket
import struct

from sockets5.enums import Socks5AuthMethod, Socks5AddressAddrType
from sockets5.socks5_req import Socks5AuthReqGen, Socks5AddrReqGen
from sockets5.socks5_rsp import Socks5AuthRsp, Socks5AddrRsp
from utils.util import async_pull


class TCPRelay:
    def __init__(self, loop, is_sslocal, host, port, remote_host, remote_port):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("server fd:%r" % self._sock)
        self._sock.setblocking(False)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self._sock.bind((host, port))
        self._sock.listen(socket.SOMAXCONN)
        self._loop = loop
        self._is_sslocal = is_sslocal
        self._host = host
        self._port = port
        self._remote_host = remote_host
        self._remote_port = remote_port

    async def accept(self):
        while True:
            csock, address = await self._loop.sock_accept(self._sock)
            print("connect from :", address)
            self._loop.create_task(
                TCPRelayHandler(self, self._loop, csock).relay()
            )

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def remote_host(self):
        return self._remote_host

    @property
    def remote_port(self):
        return self._remote_port

    @property
    def is_sslocal(self):
        return self._is_sslocal


class ConnectionClosedError(Exception):
    pass


class TCPRelayHandler:
    def __init__(self, config, loop, sock):
        self._sock = sock
        self._remote_sock = None
        self._loop = loop
        self._config = config
        self._upstream = None
        self._downstream = None
        self._sock.setblocking(False)

    async def authorize(self):
        auth_req = await async_pull(Socks5AuthReqGen(), self._loop, self._sock)
        print("auth_req:", auth_req)
        await self._loop.sock_sendall(
            self._sock, Socks5AuthRsp(Socks5AuthMethod.NO_AUTH)
        )
        print("send auth req done!")
        return auth_req

    async def address(self):
        print("start address", self._sock)
        addr_req = await async_pull(Socks5AddrReqGen(), self._loop, self._sock)
        print("addr_req:", addr_req)
        addr_rsp = Socks5AddrRsp(
            Socks5AddressAddrType.IP4, b"\x00.\x00.\x00.\x00", 5677
        )
        print("addr_rsp:", addr_rsp)
        await self._loop.sock_sendall(self._sock, addr_rsp)
        self._remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._remote_sock.setblocking(False)
        await self._loop.sock_connect(
            self._remote_sock,
            (self._config.remote_host, self._config.remote_port),
        )
        await self._loop.sock_sendall(self._remote_sock, addr_req.bypass)
        return addr_req

    async def upstream(self):
        while True:
            try:
                up_ = await self._loop.sock_recv(self._sock, 4096)
                await self._loop.sock_sendall(self._remote_sock, up_)
            except BrokenPipeError:
                self._loop.remove_reader(self._sock.fileno())
                self._loop.remove_writer(self._remote_sock.fileno())
                self._downstream.cancel()
                break
            except asyncio.CancelledError:
                self._sock.close()
                self._remote_sock.close()
                break

    async def downstream(self):
        while True:
            try:
                down_ = await self._loop.sock_recv(self._remote_sock, 4096)
                await self._loop.sock_sendall(self._sock, down_)
            except BrokenPipeError:
                self._loop.remove_reader(self._remote_sock.fileno())
                self._loop.remove_writer(self._sock.fileno())
                self._upstream.cancel()
                break
            except asyncio.CancelledError:
                self._remote_sock.close()
                self._sock.close()
                break
        
    async def pipe(self):
        while True:
            try:
                up_ = await asyncio.wait_for(
                    self._loop.sock_recv(self._sock, 4096), timeout=0.1
                )
                await asyncio.wait_for(
                    self._loop.sock_sendall(self._remote_sock, up_),
                    timeout=0.1,
                )
                down_ = await asyncio.wait_for(
                    self._loop.sock_recv(self._remote_sock, 4096), timeout=0.1
                )
                await asyncio.wait_for(
                    self._loop.sock_sendall(self._sock, down_), timeout=0.1
                )
            except asyncio.TimeoutError:
                continue
            except BrokenPipeError:
                self._remote_sock.close()
                self._sock.close()
                print("pipe exit!")
                break

    async def relay(self):
        res = await self.authorize()
        if not res:
            return None
        
        res = await self.address()
        print("Start streaming <****>")
        self._downstream = self._loop.create_task(self.downstream())
        self._upstream = self._loop.create_task(self.upstream())
        if not res:
            return None
        await asyncio.gather(self._upstream, self._downstream)
        # await self._loop.create_task(self.pipe())
        print("relay exit!!!!!!!!!!!!!!!!!")
