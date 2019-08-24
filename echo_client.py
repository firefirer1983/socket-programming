import sys
import logging
import socket
from eventloop import EventLoop
from selectors import EVENT_READ, EVENT_WRITE

log = logging.getLogger('echo-client')
log.addHandler(logging.StreamHandler(sys.stdout))

loop = EventLoop()

buf = b'hello world'

SEND_MAX = len(buf)


def _echo(sock, mask):
    global buf
    try:
        if mask & EVENT_READ:
            received = sock.recv(1024)
            if not received:
                loop.remove(sock)
                sock.close()
            else:
                buf += received
                print('echo:', received)
        elif mask & EVENT_WRITE:
            sent = sock.sendall(buf[:SEND_MAX])
            buf = buf[:sent]
    except ConnectionResetError as e:
        log.error('reset by peer')
        log.exception(e)
        loop.remove(sock)
        sock.close()
        

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setblocking(False)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    loop.add(s, EVENT_READ | EVENT_WRITE, _echo)
    s.connect_ex(('127.0.0.1', 1080))
    loop.run()
    

