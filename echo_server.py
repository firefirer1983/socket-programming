import logging
import socket
import sys

from eventloop import EventLoop
from selectors import EVENT_READ, EVENT_WRITE

log = logging.getLogger('echo-server')
log.addHandler(logging.StreamHandler(sys.stdout))


loop = EventLoop()
buf = b''
SEND_MAX = 11


def _on_accept(sock, mode):
    print('==> on accept', sock.fileno(), mode)
    csock, address = sock.accept()
    loop.add(csock, EVENT_READ | EVENT_WRITE, _on_event)


def _on_event(sock, mode):
    global buf
    try:
        if mode & EVENT_READ:
            received = sock.recv(1024)
            if received:
                buf += received
            else:
                loop.remove(sock)
        elif mode & EVENT_WRITE:
            if len(buf) >= SEND_MAX:
                sent = sock.sendall(buf[:SEND_MAX])
            else:
                sent = sock.sendall(buf)
            buf = buf[:sent]
    except ConnectionResetError as e:
        log.exception(e)
        log.error('reset by peer')
        loop.remove(sock)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setblocking(False)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    s.bind(('127.0.0.1', 5566))
    s.listen(socket.SOMAXCONN)
    loop.add(s, EVENT_READ, _on_accept)
    loop.run()
