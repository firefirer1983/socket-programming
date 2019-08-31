import socket
from collections import namedtuple
from datafields import UnsignedIntegerField, RawBytesField
from selectors import EVENT_READ, EVENT_WRITE
from eventloop import EventLoop


AuthReq = namedtuple("AuthReq", "ver cmd atype addr")


class Socks5AuthReq:
    
    def __new__(cls):
        ver = yield from UnsignedIntegerField(1)
        cmd =  yield from UnsignedIntegerField(1)
        rsv = yield from RawBytesField(1)
        if rsv != b"\x00":
            raise RuntimeError("Error rsv field")
        atype = yield from RawBytesField(1)
        if atype == b"\x01":
            addr = yield from RawBytesField(4)
        elif atype == b"\x04":
            addr = yield from RawBytesField(16)
        else:
            raise RuntimeError("Not support atype:", atype)
        return AuthReq(ver, cmd, atype, addr)
    

if __name__ == '__main__':
    loop = EventLoop()
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setblocking(False)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        loop.add(s, EVENT_READ|EVENT_WRITE, )
        