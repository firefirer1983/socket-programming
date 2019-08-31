import struct
from enum import Enum, unique

from exc import Sock5AuthorizeErr
from utils.util import ignored_stop, Response
from datafields import UnsignedIntegerField, StringField, UndefinedField, \
    I8ArrayField, RawBytesField

SOCKS5_VER = 5


@unique
class Socks5AddressCmd(Enum):
    CONNECT = 0x01
    BIND = 0x02
    UDP_ASSOCIATE = 0x04


@unique
class Socks5AddressAddrType(Enum):
    IP4 = 0x01
    DOMAINNAME = 0x03
    IP6 = 0x04


@unique
class Socks5AuthMethod(Enum):
    NO_AUTH = 0x00
    GSSAPI = 0x01
    USRNAME_PWD = 0x02
    IANA_ASSIGNED = 0x03
    PRIVATE_RSV = 0x80
    NO_ACCEPTABLE = 0xFF


class CompositeField:
    
    def __init__(self, init_length):
        super().__init__(init_length)
    
    def gen(self):
        meta = UnsignedIntegerField(self._length)
        gen = meta.gen()
        data = None
        while True:
            try:
                data = gen.send(data)
                print('gen.send', data)
                data = yield data
                print("get data", data)
            except StopIteration:
                break
        
        variable_len = meta.unpack()
        
        string = StringField(variable_len)
        gen = string.gen()
        data = None
        with ignored_stop():
            yield gen.send(data)
            print("send again")
        
        self._bytes = yield gen.send(data.length)


class DoneUnpacked(StopIteration):
    pass


class Socks5AuthRequest:
    
    def __init__(self, *args):
        if len(args) < 1:
            raise RuntimeError("at least one method is need")
        
        auth_method_cnt = len(args)
        pack_fmt = ">" + "BB" + "B" * auth_method_cnt
        
        methods = [arg.value for arg in args]
        print(pack_fmt, args, methods)
        self._data = struct.pack(pack_fmt, SOCKS5_VER, auth_method_cnt, *methods)
    
    def to_bytes(self) -> bytes:
        return self._data


class Socks5AddressRequest:
    _rsv = 0
    
    def __init__(self, cmd, atype, addr, port):
        
        addr_len = len(addr)
        if atype == Socks5AddressAddrType.DOMAINNAME:
            self._data = struct.pack((">BBBBB%ush" % addr_len),
                                     SOCKS5_VER, cmd.value, self._rsv, atype.value, addr_len, addr, port)
        elif atype == Socks5AddressAddrType.IP4 or atype == Socks5AddressAddrType.IP6:
            self._data = struct.pack((">BBBB%ush" % addr_len),
                                     SOCKS5_VER, cmd.value, self._rsv, atype.value, addr, port)
    
    def to_bytes(self) -> bytes:
        return self._data


class Socks5AddressRsp(Response):
    _fields = dict(ver=UnsignedIntegerField(1),
                   cmd=UnsignedIntegerField(1),
                   rsv=UnsignedIntegerField(1),
                   atyp=UnsignedIntegerField(1),
                   addr=UndefinedField(),
                   port=UnsignedIntegerField(2))
    
    def gen(self):
        for field_name in self._fields.keys():
            field = self._fields[field_name]
            yield from self._pipe_to_field(field.gen())
            if field_name == 'atyp':
                if field.unpack() == Socks5AddressAddrType.IP4.value:
                    print("ipv4")
                    self._fields['addr'] = StringField(4)
                elif field.unpack() == Socks5AddressAddrType.IP6.value:
                    print("ipv6")
                    self._fields['addr'] = StringField(16)
                elif field.unpack() == Socks5AddressAddrType.DOMAINNAME.value:
                    print("domain")
                    self._fields['addr'] = CompositeField(1)
    
    def pull(self, sock):
        self._pull_from_sock(self.gen(), sock)
        return {k: v.unpack() for k, v in self._fields.items()}


class Socks5AuthRsp(Response):
    _fields = dict(
        ver=UnsignedIntegerField(1),
        method=UnsignedIntegerField(1),
    )
    
    def gen(self):
        for field_name in self._fields.keys():
            field = self._fields[field_name]
            yield from self._pipe_to_field(field.gen())
    
    def pull(self, sock):
        self._pull_from_sock(self.gen(), sock)
        return {k: v.unpack() for k, v in self._fields.items()}

    def __call__(self, octets):
        ver = yield from RawBytesField(1)
        if ver != b"\x05":
            raise Sock5AuthorizeErr("not ver sock5")
        nmethod = yield from UnsignedIntegerField(1)
        methods = yield from I8ArrayField(nmethod)
        
