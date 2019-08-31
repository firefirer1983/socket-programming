import asyncio
import socket
from struct import pack

from datafields import UnsignedIntegerField, RawBytesField, StringField
from sockets5.enums import (
    Socks5AuthMethod,
    Socks5RepType,
    Socks5AddressAddrType,
)
from utils.util import async_pull
from collections import namedtuple

HOST = "127.0.0.1"
PORT = 1090

AuthReq = namedtuple("AuthReq", "ver nmethod methods")
AddrReq = namedtuple("AddrReq", "ver cmd srv atype addr")


class Socks5AuthReq:
    def __new__(cls):
        ver = yield from UnsignedIntegerField(1)
        print("ver:", ver)
        if ver != 5:
            return None

        nmethods = yield from UnsignedIntegerField(1)
        print("nmethods:", nmethods)

        if not 0 < nmethods < 255:
            return None

        methods = yield from RawBytesField(nmethods)
        print("methods:", methods)

        return AuthReq(ver, nmethods, methods)


class Socks5AddrReq:
    def __new__(cls):
        ver = yield from UnsignedIntegerField(1)
        print("ver:", ver)
        if ver != 5:
            return None

        cmd = yield from UnsignedIntegerField(1)
        print("cmd:", cmd)

        rsv = yield from RawBytesField(1)

        if rsv != b"\x00":
            return None

        atype = yield from RawBytesField(1)

        if atype == b"\x01":
            addr = yield from RawBytesField(4)
        elif atype == b"\x03":
            name_len = yield from UnsignedIntegerField(1)
            addr = yield from StringField(name_len)
        elif atype == b"\x04":
            addr = yield from RawBytesField(16)
        else:
            raise RuntimeError("Unknown atype:", atype)
        return AddrReq(ver, cmd, rsv, atype, addr)


class Socks5AuthRsp:
    def __init__(self, auth_method):
        self._ver = 5
        self._auth_method = auth_method

    def to_bytes(self):
        return pack("!BB", self._ver, self._auth_method.value)


class Socks5AddrRsp:
    def __init__(self, atyp, addr, port):
        self._ver = 5
        self._rep = Socks5RepType.SUCCEEDED.value
        self._rsv = 0
        self._atyp = atyp.value
        self._addr = addr
        self._port = port
        print("typeof port:", type(self._port))
        print(
            self._ver, self._rep, self._rsv, self._atyp, self._addr, self._port
        )

    def to_bytes(self):
        labels = [ord(p) for p in self._addr.split(b".")]
        fmt_ = "!BBBB" + "B" * len(labels) + "H"
        return pack(
            fmt_,
            self._ver,
            self._rep,
            self._rsv,
            self._atyp,
            *labels,
            self._port
        )


if __name__ == "__main__":

    loop = asyncio.get_event_loop()

    async def sock_handler(sock):
        auth_req = await async_pull(Socks5AuthReq(), loop, sock)
        print("auth_req:", auth_req)
        await loop.sock_sendall(
            sock, Socks5AuthRsp(Socks5AuthMethod.NO_AUTH).to_bytes()
        )
        print("auth_rsp:", Socks5AuthRsp(Socks5AuthMethod.NO_AUTH).to_bytes())
        addr_req = await async_pull(Socks5AddrReq(), loop, sock)
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

    async def server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
            s.setblocking(False)
            s.bind((HOST, PORT))
            s.listen(socket.SOMAXCONN)
            while True:
                csock, address = await loop.sock_accept(s)
                print("connect from :", address)
                loop.create_task(sock_handler(csock))

    loop.create_task(server())
    loop.run_forever()
