from collections import OrderedDict
from contextlib import contextmanager
from struct import *
from except_handler import exception_handle
import socket
from enum import Enum, unique


HOST = "127.0.0.1"
PORT = 1080


DST_ADDR = b"google.com"
DST_PORT = 80
VER = 5
CONNECT_CMD = 1
IP4_ATYP = 3


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


class Data:
    
    def __init__(self, length):
        self._length = length
        self._bytes = None
    
    def _unpack(self, fmt):
        return unpack(fmt, self._bytes)[0]
    
    @property
    def size(self):
        return len(self._bytes)


class UndefinedField:
    pass


class UnsignedIntegerField(Data):
    
    def __init__(self, length):
        super().__init__(length)
        if self._length == 1:
            self._fmt = '>' + 'B'
        elif self._length == 2:
            self._fmt = '>' + 'H'
        elif self._length == 4:
            self._fmt = '>' + 'I'
        elif self._length == 8:
            self._fmt = '>' + 'Q'
    
    def gen(self):
        self._bytes = yield self._length
    
    def unpack(self):
        return super()._unpack(self._fmt)


class StringField(Data):
    
    def __init__(self, length):
        super().__init__(length)
        self._fmt = '>' + '%u' % length + 's'

    def gen(self):
        self._bytes = yield self._length
    
    def unpack(self):
        return super()._unpack(self._fmt)


@contextmanager
def ignored_stop():
    try:
        yield
    except StopIteration:
        pass


class CompositeField(Data):
    
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


class IntegerArrayField(Data):
    
    def __init__(self, length):
        super().__init__(length)
        self._fmt = '>' + 'B' * length

    def gen(self):
        self._bytes = yield self._length
    
    def unpack(self):
        return super()._unpack(self._fmt)


class DoneUnpacked(StopIteration):
    pass


class Socks5AuthRequest:
    
    _ver = 5
    
    def __init__(self, *args):
        
        if len(args) < 1:
            raise RuntimeError("at least one method is need")
        
        auth_method_cnt = len(args)
        pack_fmt = ">" + "BB" + "B" * auth_method_cnt
        
        methods = [arg.value for arg in args]
        print(pack_fmt, args, methods)
        self._data = pack(pack_fmt, self._ver, auth_method_cnt, *methods)
    
    def to_bytes(self)->bytes:
        return self._data
    

class Socks5AddressRequest:
    _ver = 5
    _rsv = 0
    
    def __init__(self, cmd, atype, addr, port):
        
        addr_len = len(addr)
        if atype == Socks5AddressAddrType.DOMAINNAME:
            self._data = pack((">BBBBB%ush" % addr_len),
                              self._ver, cmd.value, self._rsv, atype.value, addr_len, addr, port)
        elif atype == Socks5AddressAddrType.IP4 or atype == Socks5AddressAddrType.IP6:
            self._data = pack((">BBBB%ush" % addr_len),
                              self._ver, cmd.value, self._rsv, atype.value, addr, port)
            
    def to_bytes(self)->bytes:
        return self._data


class Response:
    
    @staticmethod
    def _pull_from_sock(g, sock):
        data = None
        while True:
            try:
                len_ = g.send(data)
                data = sock.recv(len_)
            except StopIteration:
                break
                
    @staticmethod
    def _pull_from_field(g):
        data = None
        while True:
            try:
                data = yield g.send(data)
            except StopIteration:
                break


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
            yield from self._pull_from_field(field.gen())
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
            yield from self._pull_from_field(field.gen())
        
    def pull(self, sock):
        self._pull_from_sock(self.gen(), sock)
        return {k: v.unpack() for k, v in self._fields.items()}


@exception_handle(self_=False)
def get_auth_rsp(csock):
    auth_req = Socks5AuthRequest(Socks5AuthMethod.NO_ACCEPTABLE)
    csock.sendall(auth_req.to_bytes())
    auth_method_raw = csock.recv(1024)
    assert len(auth_method_raw) == 2
    ver, method = auth_method_raw[0], auth_method_raw[1]
    print("ver:%u method:%u" % (ver, method))
    return method


def try_address(csock):
    host_length = len(DST_ADDR)
    pack_fmt = ">BBBBB%ush" % host_length
    print('pack_fmt', pack_fmt)
    # csock.sendall(pack(pack_fmt, VER, CONNECT_CMD, 0, IP4_ATYP, host_length, DST_ADDR, DST_PORT))
    addr_req = Socks5AddressRequest(Socks5AddressCmd.CONNECT, Socks5AddressAddrType.DOMAINNAME, DST_ADDR, DST_PORT)
    csock.sendall(addr_req.to_bytes())
    addr_res = csock.recv(1024)
    addr_len = len(addr_res) - 6
    fmt = ">BBBB%ush" % addr_len
    ver, rep, rsv, atyp, addr, port = unpack(fmt, addr_res)
    print(ver, rep, rsv, atyp, addr, port)
    if rep != 0:
        raise RuntimeError("connect fail")
    return addr, port


def client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        s.connect((HOST, PORT))
        method = get_auth_rsp(s)
        addr, port = try_address(s)
        

if __name__ == '__main__':
    client()
