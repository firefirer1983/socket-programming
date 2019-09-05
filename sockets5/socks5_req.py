from collections.__init__ import namedtuple
from struct import pack

from datafields import UnsignedIntegerField, RawBytesField, StringField
from sockets5.enums import Socks5AddressAddrType

AuthReq = namedtuple("AuthReq", "ver nmethod methods")
# AddrReq = namedtuple("AddrReq", "ver cmd srv atype addr")


class AddrReq:
    def __init__(self, ver, cmd, srv, atyp, addr, port):
        self._ver = ver
        self._cmd = cmd
        self._rsv = srv
        self._atyp = atyp
        self._addr = addr
        self._port = port
        print(
            self._ver, self._cmd, self._rsv, self._atyp, self._addr, self._port
        )

    @property
    def ver(self):
        return self._ver

    @property
    def cmd(self):
        return self._cmd

    @property
    def rsv(self):
        return self._rsv

    @property
    def addr(self):
        return self._addr

    @property
    def port(self):
        return self._port

    @property
    def bypass(self):
        fmt_ = "!BB" + "%us" % len(self._addr) + "H"
        return pack(fmt_, self._atyp, len(self._addr), self._addr, self._port)

    def to_bytes(self):
        return pack("!BB", self._ver, self._cmd) + self._rsv + self.bypass


class Socks5AuthReqGen:
    def __new__(cls):
        ver = yield from UnsignedIntegerField(1)
        if ver != 5:
            return None

        nmethods = yield from UnsignedIntegerField(1)

        if not 0 < nmethods < 255:
            return None

        methods = yield from RawBytesField(nmethods)
        print("methods:", methods)

        return AuthReq(ver, nmethods, methods)


class Socks5AddrReqGen:
    def __new__(cls):
        ver = yield from UnsignedIntegerField(1)
        if ver != 5:
            return None

        cmd = yield from UnsignedIntegerField(1)

        rsv = yield from RawBytesField(1)

        if rsv != b"\x00":
            return None

        atype = yield from UnsignedIntegerField(1)

        if atype == 1:
            addr = yield from RawBytesField(4)
        elif atype == 3:
            name_len = yield from UnsignedIntegerField(1)
            addr = yield from StringField(name_len)
        elif atype == 4:
            addr = yield from RawBytesField(16)
        else:
            raise RuntimeError("Unknown atype:", atype)

        port = yield from UnsignedIntegerField(2)
        return AddrReq(ver, cmd, rsv, atype, addr, port)


class Socks5AuthRequest:

    _ver = 5

    def __new__(cls, *args):
        if len(args) < 1:
            raise RuntimeError("at least one method is need")

        auth_method_cnt = len(args)
        pack_fmt = "!BB" + "B" * auth_method_cnt

        methods = [arg.value for arg in args]
        return pack(pack_fmt, cls._ver, auth_method_cnt, *methods)

    # def __init__(self, *args):
    #
    #     if len(args) < 1:
    #         raise RuntimeError("at least one method is need")
    #
    #     auth_method_cnt = len(args)
    #     pack_fmt = "!BB" + "B" * auth_method_cnt
    #
    #     methods = [arg.value for arg in args]
    #     self._data = pack(pack_fmt, self._ver, auth_method_cnt, *methods)
    #
    # def to_bytes(self) -> bytes:
    #     return self._data


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
