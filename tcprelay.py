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
        self._loop = loop
        self._is_sslocal = is_sslocal

    async def authorize(self):
        auth_req = await async_pull(Socks5AuthReqGen(), self._loop, self._sock)
        print("auth_req:", auth_req)
        await self._loop.sock_sendall(
            self._sock, Socks5AuthRsp(Socks5AuthMethod.NO_AUTH).to_bytes()
        )
        addr_req = await async_pull(Socks5AddrReqGen(), self._loop, self._sock)
        print("addr_req:", addr_req)
        rsp = Socks5AddrRsp(
            Socks5AddressAddrType.IP4, b"\x00.\x00.\x00.\x00", 5677
        )
        print("rsp: ", rsp)
        addr_rsp = rsp.to_bytes()
        print("addr rsp: %r" % addr_rsp)
        await self._loop.sock_sendall(self._sock, addr_rsp)
        return addr_rsp

    async def relay(self):
        auth_res = await self.authorize()
        print("auth_res:", auth_res)
        if not auth_res:
            return None
        
        

