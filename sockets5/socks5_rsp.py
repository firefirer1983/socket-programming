from collections.__init__ import namedtuple
from struct import pack

from datafields import UnsignedIntegerField, RawBytesField, StringField
from sockets5.enums import Socks5RepType


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
        if isinstance(self._addr, str):
            labels = [int(p) for p in self._addr.split(".")]
        else:
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


AuthRsp = namedtuple("AuthRsp", "ver method")
AddrRsp = namedtuple("AddrRsp", "ver rep rsv atyp addr port")


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
