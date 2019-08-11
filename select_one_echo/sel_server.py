import types
import socket
import selectors


select = selectors.DefaultSelector()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    s.setblocking(False)
    s.bind(('127.0.0.1', 5566))
    s.listen(10)
    print('READ:', selectors.EVENT_READ, 'WRITE:', selectors.EVENT_WRITE)
    select.register(s, selectors.EVENT_READ)
    while True:
        events = select.select(timeout=None)
        for key, mask in events:
            if mask & selectors.EVENT_READ:
                if not key.data:
                    csock, address = s.accept()
                    print('connect from ', address)
                    select.register(csock,
                                    selectors.EVENT_READ|selectors.EVENT_WRITE,
                                    data=types.SimpleNamespace(in_buf=b'', out_buf=b''))
                else:
                    csock = key.fileobj
                    received = csock.recv(1024)
                    if not received:
                        select.unregister(csock)
                        csock.close()
                        break
                    print('received:', received)
                    key.data.in_buf += received
            
            if mask & selectors.EVENT_WRITE:
                csock = key.fileobj
                sent = csock.send(key.data.out_buf[:11])
                key.data.out_buf = key.data.out_buf[sent:]

            if key.data:
                key.data.out_buf += key.data.in_buf
                key.data.in_buf = b''
