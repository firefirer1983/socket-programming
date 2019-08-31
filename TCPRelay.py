from collections import namedtuple, MutableMapping

from eventloop import EventLoop
from selectors import EVENT_READ, EVENT_WRITE
import socket

from exc import Sock5AuthorizeErr
from utils.loggers import get_logger


log = get_logger("TCPRelay")


class SocksPipes(MutableMapping):
    
    def __init__(self):
        self._pipes = {}
    
    def __setitem__(self, key, value):
        self._pipes[key] = value
    
    def __getitem__(self, item):
        return self._pipes[item]
    
    def __iter__(self):
        return iter(self._pipes)
    
    def __len__(self):
        return len(self._pipes)
    
    def __delitem__(self, key):
        del self._pipes[key]
        

class TCPRelay:
    def __init__(self, loop: EventLoop):
        self._acceptor_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._acceptor_sock.setblocking(False)
        self._acceptor_sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, True
        )
        self._loop = loop
        self._pipes = SocksPipes()

    def add_to_loop(self):
        self._loop.add(self._acceptor_sock, EVENT_READ | EVENT_WRITE, self)

    def __call__(self, sock, mask):
        # new connection
        
        if sock == self._acceptor_sock:
            if mask & EVENT_READ:
                csock, addrinfo = self._acceptor_sock.accept()
                self._pipes[csock] = None
                TCPRelayLocal(csock, self._loop, False).add_to_loop()


class TCPRelayLocal:
    def __init__(self, sock, loop: EventLoop, is_sslocal):
        self._loop = loop
        self._sock = sock
        self._is_sslocal = is_sslocal
        self._authorized = False
        self._sock5_authorizer = None
        self._authorization_len = 4
        self._received = None

    def add_to_loop(self):
        self._loop.add(self._sock, EVENT_READ | EVENT_WRITE, self)

    def __call__(self, sock, mask):
        if mask & EVENT_READ:

            if not self._authorized:
                try:
                    len_ = self._sock5_authorizer(self._received)
                    if len_ == 0:
                        self._authorized = True
                        return
                except Sock5AuthorizeErr as e:
                    log.exception(e)
                    self._received = None
                    sock.close()
                    self._loop.remove(sock)
                    return
                else:
                    self._received, addr = sock.recv(len_)

    def is_authorized(self):
        return self._authorized

        
class TCPRelayRemote:
    def __init__(self, sock, loop: EventLoop, is_sslocal):
        self._loop = loop
        self._sock = sock
        self._is_sslocal = is_sslocal

    def add_to_loop(self):
        self._loop.add(self._sock, EVENT_READ | EVENT_WRITE, self)

    def __call__(self, sock, mask):
        if mask & EVENT_READ:
            pass
