import asyncio
import socket
from struct import pack
from utils.loggers import get_logger

from datafields import UnsignedIntegerField, RawBytesField, StringField
from sockets5.enums import (
    Socks5AuthMethod,
    Socks5AddressAddrType,
    Socks5AddressCmd,
)
from utils.util import async_pull
from collections import namedtuple


log = get_logger("socks5-client")

loop = asyncio.get_event_loop()
HOST = "127.0.0.1"
PORT = 1090

AuthRsp = namedtuple("AuthRsp", "ver method")
AddrRsp = namedtuple("AddrRsp", "ver rep rsv atyp addr port")


class Socks5AddrRsp:
    def __new__(cls):
        ver = yield from UnsignedIntegerField(1)
        if ver != 5:
            return None

        rep = yield from UnsignedIntegerField(1)

        rsv = yield from RawBytesField(1)
        assert rsv == b"\x00"

        atyp = yield from RawBytesField(1)

        if atyp == b"\01":
            addr = yield from RawBytesField(4)
        elif atyp == b"\03":
            name_len = yield from UnsignedIntegerField(1)
            addr = yield from StringField(name_len)
        elif atyp == b"\04":
            addr = yield from RawBytesField(16)
        else:
            raise RuntimeError("Unknown atyp:", atyp)

        port = yield from UnsignedIntegerField(2)

        return AddrRsp(ver, rep, rsv, atyp, addr, port)


class Socks5AuthRequest:

    _ver = 5

    def __init__(self, *args):

        if len(args) < 1:
            raise RuntimeError("at least one method is need")

        auth_method_cnt = len(args)
        pack_fmt = "!BB" + "B" * auth_method_cnt

        methods = [arg.value for arg in args]
        self._data = pack(pack_fmt, self._ver, auth_method_cnt, *methods)

    def to_bytes(self) -> bytes:
        return self._data


class Socks5AddrRequest:
    _ver = 5
    _rsv = 0

    def __init__(self, cmd, atyp, addr, port):

        addr_len = len(addr)
        if atyp == Socks5AddressAddrType.DOMAINNAME:
            self._data = pack(
                (">BBBBB%ush" % addr_len),
                self._ver,
                cmd.value,
                self._rsv,
                atyp.value,
                addr_len,
                addr,
                port,
            )
        elif (
            atyp == Socks5AddressAddrType.IP4
            or atyp == Socks5AddressAddrType.IP6
        ):
            self._data = pack(
                (">BBBB%ush" % addr_len),
                self._ver,
                cmd.value,
                self._rsv,
                atyp.value,
                addr,
                port,
            )

    def to_bytes(self) -> bytes:
        return self._data


class Socks5AuthRsp:
    def __new__(cls):
        ver = yield from UnsignedIntegerField(1)
        if ver != 5:
            return None

        method = yield from UnsignedIntegerField(1)

        return AuthRsp(ver, method)


if __name__ == '__main__':

    async def client():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
            sock.setblocking(False)
            await loop.sock_connect(sock, (HOST, PORT))
            await loop.sock_sendall(
                sock, Socks5AuthRequest(Socks5AuthMethod.NO_AUTH).to_bytes()
            )
            auth_rsp = await async_pull(Socks5AuthRsp(), loop, sock)
            log.info(f"auth_rsp: {auth_rsp}")
            addr_req = Socks5AddrRequest(
                Socks5AddressCmd.CONNECT,
                Socks5AddressAddrType.DOMAINNAME,
                b"google.com",
                80,
            ).to_bytes()
            await loop.sock_sendall(sock, addr_req)
            addr_rsp = await async_pull(Socks5AddrRsp(), loop, sock)
            log.info("addr_rsp:%r" % addr_rsp)
            loop.stop()
    
    
    loop.create_task(client())
    loop.run_forever()
