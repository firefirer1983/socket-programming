from collections.__init__ import namedtuple
from enum import Enum
from struct import pack

from datafields import UnsignedIntegerField, RawBytesField, StringField
from sockets5.enums import Socks5RepType


class Socks5AuthRsp:
    def __new__(cls, auth_method):
        ver = 5
        auth_method = auth_method
        return pack("!BB", ver, auth_method.value)


class Socks5AddrRsp:
    def __new__(cls, atyp, addr, port):
        ver = 5
        rep = Socks5RepType.SUCCEEDED.value
        rsv = 0
        if isinstance(atyp, Enum):
            atyp = atyp.value
        addr = addr
        port = port
        if isinstance(addr, str):
            labels = [int(p) for p in addr.split(".")]
        else:
            labels = [ord(p) for p in addr.split(b".")]
        fmt_ = "!BBBB" + "B" * len(labels) + "H"
        return pack(fmt_, ver, rep, rsv, atyp, *labels, port)


AuthRsp = namedtuple("AuthRsp", "ver method")


class AddrRsp(namedtuple("AddrRsp", "ver rep rsv atyp addr port")):
    def to_bytes(self):
        print(
            "======> ",
            self.ver,
            self.rep,
            self.rsv,
            self.atyp,
            self.addr,
            self.port,
        )
        return (
            pack("!BB", self.ver, self.rep)
            + self.rsv
            + self.atyp
            + self.addr
            + pack("!H", self.port)
        )


class Socks5AddrRspGen:
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


class Socks5AuthRspGen:
    def __new__(cls):
        ver = yield from UnsignedIntegerField(1)
        if ver != 5:
            return None

        method = yield from UnsignedIntegerField(1)

        return AuthRsp(ver, method)
