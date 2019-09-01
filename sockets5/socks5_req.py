from collections.__init__ import namedtuple
from struct import pack

from datafields import UnsignedIntegerField, RawBytesField, StringField
from sockets5.enums import Socks5AddressAddrType

AuthReq = namedtuple("AuthReq", "ver nmethod methods")
AddrReq = namedtuple("AddrReq", "ver cmd srv atype addr")


class Socks5AuthReqGen:
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


class Socks5AddrReqGen:
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
