import struct
import socket
from contextlib import contextmanager


class Data:
    
    def __init__(self, length):
        self._length = length
        self._bytes = b''
        self._fmt = None
    
    def unpack(self):
        res_ = struct.unpack(self._fmt, self._bytes)
        return res_ if len(res_) > 1 else res_[0]
    
    @property
    def size(self):
        return len(self._bytes)


class UndefinedField:
    pass


@contextmanager
def ignored_stop():
    try:
        yield
    except StopIteration:
        pass


def pull_diagram_sock(g, sock):
    data, addr = sock.recvfrom(1024)
    print("pulled %u bytes from udp socket:" % len(data))
    print(data)
    prev_offs_ = 0
    len_ = next(g)
    offset = 0
    while True:
        octets = data[offset:len_ + offset]
        print("offset:%u len:%u pull:" % (offset, len_), octets)
        ret_ = g.send(octets)
        if not isinstance(ret_, tuple):
            offset += len_
            len_ = ret_
        else:
            if ret_[0] > 0:
                prev_offs_ = offset
                offset = ret_[0]
                len_ = ret_[1]
            else:
                offset = prev_offs_
                len_ = ret_[1]


def pull_stream_sock(g, sock):
    data = None
    while True:
        len_ = g.send(data)
        data, addr = sock.recvfrom(len_)


class Response:
    
    @staticmethod
    def _pull_from_sock(g, sock):
        data = None
        while True:
            len_ = g.send(data)
            if sock.type == socket.SOCK_DGRAM:
                data, addr = sock.recvfrom(len_)
            else:
                data = sock.recv(len_)
    
    @staticmethod
    def _pipe_to_field(g):
        data = None
        while True:
            try:
                data = yield g.send(data)
            except StopIteration:
                break


def unpacks(fmt, data):
    unpacked = struct.unpack(fmt, data)
    return unpacked[0] if len(unpacked) == 1 else unpacked


class UdpBufCursor:
    
    def __init__(self):
        self._save_point = 0
        self._offset = 0
    
    @property
    def offset(self):
        return self._offset

    def preserve(self, offs):
        self._save_point = self._offset
        self._offset = offs
    
    def restore(self):
        self._offset = self._save_point

    def forward(self, steps):
        self._offset += steps
    
    def backward(self, steps):
        self._offset -= steps

