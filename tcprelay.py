import asyncio
import socket

from async_dns.resolver import DnsResolver
from sockets5.enums import Socks5AuthMethod, Socks5AddressAddrType
from sockets5.socks5_req import Socks5AuthReqGen, Socks5AddrReqGen
from sockets5.socks5_rsp import Socks5AuthRsp, Socks5AddrRsp, Socks5AddrRspGen
from utils.util import async_pull
from utils.loggers import get_logger

log = get_logger("tcprelay")


class TCPRelay:
    def __init__(
        self,
        loop,
        is_sslocal,
        sslocal_host,
        sslocal_port,
        ssserver_host=None,
        ssserver_port=None,
    ):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("server fd:%r" % self._sock)
        self._sock.setblocking(False)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        self._sock.bind((sslocal_host, sslocal_port))
        self._sock.listen(socket.SOMAXCONN)
        self._loop = loop
        self._is_sslocal = is_sslocal
        self._sslocal_host = sslocal_host
        self._sslocal_port = sslocal_port
        self._ssserver_host = ssserver_host
        self._ssserver_port = ssserver_port
        self._resolver = DnsResolver(self._loop, "8.8.8.8", 53)

    async def accept(self):
        while True:
            csock, address = await self._loop.sock_accept(self._sock)
            self._loop.create_task(
                TCPRelayHandler(
                    self, self._loop, self._resolver, csock
                ).relay()
            )

    @property
    def sslocal_host(self):
        return self._sslocal_host

    @property
    def sslocal_port(self):
        return self._sslocal_port

    @property
    def ssserver_host(self):
        return self._ssserver_host

    @property
    def ssserver_port(self):
        return self._ssserver_port

    @property
    def is_sslocal(self):
        return self._is_sslocal


class TCPRelayHandler:
    def __init__(self, config: TCPRelay, loop, resolver, sock):
        self._sock = sock
        self._remote_sock = None
        self._loop = loop
        self._config = config
        self._upstream = None
        self._downstream = None
        self._sock.setblocking(False)
        self._resolver = resolver

    async def authorize(self):
        auth_req = await async_pull(Socks5AuthReqGen(), self._loop, self._sock)
        print("auth_req:", auth_req)
        await self._loop.sock_sendall(
            self._sock, Socks5AuthRsp(Socks5AuthMethod.NO_AUTH)
        )
        return auth_req

    async def address(self):

        self._remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._remote_sock.setblocking(False)
        addr_req = await async_pull(Socks5AddrReqGen(), self._loop, self._sock)
        print("addr_req:", addr_req)

        if self._config.is_sslocal:

            await self._loop.sock_connect(
                self._remote_sock,
                (self._config.ssserver_host, self._config.ssserver_port),
            )
            await self._loop.sock_sendall(
                self._remote_sock, addr_req.to_bytes()
            )
            addr_rsp = await async_pull(
                Socks5AddrRspGen(), self._loop, self._remote_sock
            )
            addr_rsp = addr_rsp.to_bytes()
        else:

            answer = await self._resolver.resolve(addr_req.addr)
            if not answer:
                return None
            target_ip = ".".join(["%u" % label for label in answer.rdata])
            print("target ip:", target_ip)
            await self._loop.sock_connect(self._remote_sock, (target_ip, 80))
            addr_rsp = Socks5AddrRsp(
                Socks5AddressAddrType.IP4, b"\x00.\x00.\x00.\x00", 4112
            )
        print("addr_rsp:", addr_rsp)
        if addr_rsp:
            await self._loop.sock_sendall(self._sock, addr_rsp)
        return addr_rsp

    def _stop_upstream(self):
        self._loop.remove_reader(self._sock.fileno())
        self._loop.remove_writer(self._remote_sock.fileno())

    def _stop_downstream(self):
        self._loop.remove_reader(self._remote_sock.fileno())
        self._loop.remove_writer(self._sock.fileno())

    async def upstream(self):
        while True:
            try:
                up_ = await self._loop.sock_recv(self._sock, 4096)
                if not up_:
                    raise ConnectionAbortedError
                await self._loop.sock_sendall(self._remote_sock, up_)
            except (BrokenPipeError, ConnectionAbortedError):
                self._stop_upstream()
                self._downstream.cancel()
                break
            except asyncio.CancelledError:
                self._stop_upstream()
                self._sock.close()
                self._remote_sock.close()
                break

    async def downstream(self):
        while True:
            try:
                down_ = await self._loop.sock_recv(self._remote_sock, 4096)
                if not down_:
                    raise ConnectionAbortedError
                await self._loop.sock_sendall(self._sock, down_)
            except (BrokenPipeError, ConnectionAbortedError):
                self._stop_downstream()
                self._upstream.cancel()
                break
            except asyncio.CancelledError:
                self._stop_downstream()
                self._remote_sock.close()
                self._sock.close()
                break

    async def relay(self):
        if self._config.is_sslocal:
            if not await self.authorize():
                return None

        if not await self.address():
            return None

        self._downstream = self._loop.create_task(self.downstream())
        self._upstream = self._loop.create_task(self.upstream())
        log.info(
            "%s start streaming"
            % ("sslocal" if self._config.is_sslocal else "ssserver")
        )
