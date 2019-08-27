import struct
import socket
from contextlib import contextmanager


@contextmanager
def ignored_stop():
    try:
        yield
    except StopIteration:
        pass


def pull_diagram_sock(rsp, sock):
    
    data, addr = sock.recvfrom(1024)
    p = Pool(rsp(), data)
    while True:
        try:
            p.pump()
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


class Pool:
    
    def __init__(self, g, data):
        self._pipe = g
        self.cursor = next(g)
        self._offset = 0
        self._preserve_offset = self._offset
        self._bytes = data
    
    @property
    def cursor(self):
        raise RuntimeError("cursor not readable")

    def pump(self):
        to_send = self._bytes[self._offset:self._offset + self._wait_for]
        self._offset += self._wait_for
        self.cursor = self._pipe.send(to_send)
        
    @cursor.setter
    def cursor(self, c):
        if isinstance(c, RollBackCursor):
            self._offset = self._preserve_offset
            self._wait_for = 0
        elif isinstance(c, ForwardCursor) or isinstance(c, BackwardCursor):
            self._offset += int(c)
            self._wait_for = 0
        elif isinstance(c, JumpCursor):
            self._preserve_offset = self._offset
            self._offset = int(c)
            self._wait_for = 0
        elif isinstance(c, int):
            self._wait_for = c
        else:
            raise RuntimeError("Unknown cursor type:%r" % c)
    
    @property
    def data(self):
        return self._bytes[self._offset:self._offset + self._wait_for]


class Cursor:
    
    def __init__(self, offset):
        self._offset = offset
    
    def __int__(self):
        return self._offset


class ForwardCursor(Cursor):
    
    def __init__(self, offset):
        super().__init__(offset)


class BackwardCursor(Cursor):
    def __init__(self, offset):
        super().__init__(-offset)


class RollBackCursor(Cursor):
    
    def __init__(self):
        super().__init__(0)


class JumpCursor(Cursor):
    def __init__(self, offset):
        super().__init__(offset)

