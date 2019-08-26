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


def pull_diagram_sock(rsp, sock):
    
    data, addr = sock.recvfrom(1024)
    c = Consumer(rsp(), data)
    while True:
        try:
            c.push()
        except StopIteration as e:
            return e.value
        

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


class Consumer:
    
    def __init__(self, g, data):
        self._pipe = g
        self._wait_for = next(g)
        self._offset = 0
        self._preserve_offset = self._offset
        self._bytes = data
    
    @property
    def wait_for(self):
        return self._wait_for
    
    @property
    def offset(self):
        return self._offset
    
    def push(self):
        to_send = self._bytes[self._offset:self._offset + self._wait_for]
        self._offset += self._wait_for
        
        ret_ = self._pipe.send(to_send)
        if isinstance(ret_, tuple):
            if ret_[0] > 0:
                self._preserve_offset = self._offset
                self._offset = ret_[0]
                self._wait_for = ret_[1]
            else:
                self._offset = self._preserve_offset
                self._wait_for = ret_[1]
        else:
            self._wait_for = ret_
    
    @property
    def data(self):
        return self._bytes[self._offset:self._offset + self._wait_for]
