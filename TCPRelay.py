from collections import namedtuple, MutableMapping

from eventloop import EventLoop
from selectors import EVENT_READ, EVENT_WRITE
import socket

from exc import Sock5AuthorizeErr
from sockets5.socks5_req import Socks5AuthReqGen
from utils.loggers import get_logger
from utils.util import pull_from_sock

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
    def __init__(self, loop: EventLoop, is_sslocal):
        self._acceptor_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._acceptor_sock.setblocking(False)
        self._acceptor_sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, True
        )
        self._acceptor_sock.bind((HOST, PORT))
        self._acceptor_sock.listen(socket.SOMAXCONN)
        self._loop = loop
        self._is_sslocal = is_sslocal

    def add_to_loop(self):
        self._loop.add(self._acceptor_sock, EVENT_READ | EVENT_WRITE, self)

    def __call__(self, sock, mask):
        # new connection
        log.debug("new connect :%r %r" % (sock, mask))
        if sock == self._acceptor_sock:
            if mask & EVENT_READ:
                csock, addrinfo = self._acceptor_sock.accept()
                TCPRelayLocal(
                    csock, self._loop, self._is_sslocal
                ).add_to_loop()


class TCPRelayLocal:
    def __init__(self, sock, loop: EventLoop, is_sslocal):
        self._loop = loop
        self._sock = sock
        self._is_sslocal = is_sslocal
        self._authorized = False
        self._received = None

    def add_to_loop(self):
        self._loop.add(self._sock, EVENT_READ | EVENT_WRITE, self)

    def __call__(self, sock, mask):
        if mask & EVENT_READ:

            if not self._authorized:
                auth_req = pull_from_sock(Socks5AuthReqGen(), sock)
                print(auth_req)
                if not auth_req:
                    self._loop.remove(sock)
                    sock.close()
                else:
                    self._authorized = True
        elif mask & EVENT_WRITE:
            
                print("auth_req:", auth_req)
                    
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


if __name__ == '__main__':
    loop_ = EventLoop()
    sslocal = TCPRelay(loop_, True)
    sslocal.add_to_loop()
    loop_.run()
