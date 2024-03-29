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
        events = select.select(timeout=10)
        for key, mask in events:
            if mask & selectors.EVENT_READ:
                if not key.raw_bytes:
                    csock, address = s.accept()
                    print('connect from ', address)
                    select.register(csock,
                                    selectors.EVENT_READ|selectors.EVENT_WRITE,
                                    data=types.SimpleNamespace(in_buf=b'', out_buf=b''))
                    csock.setblocking(False)
                else:
                    csock = key.fileobj
                    try:
                        received = csock.recv(1024)
                    except BlockingIOError:
                        continue
                    except ConnectionResetError:
                        csock.close()
                        select.unregister(csock)
                        continue
                    if not received:
                        select.unregister(csock)
                        csock.close()
                        break
                    print('received:', received)
                    key.raw_bytes.in_buf += received
            
            if mask & selectors.EVENT_WRITE:
                csock = key.fileobj
                try:
                    sent = csock.send(key.raw_bytes.out_buf[:11])
                except BlockingIOError:
                    continue
                except ConnectionResetError:
                    csock.close()
                    select.unregister(csock)
                    continue
                key.raw_bytes.out_buf = key.raw_bytes.out_buf[sent:]

            if key.raw_bytes:
                key.raw_bytes.out_buf += key.raw_bytes.in_buf
                key.raw_bytes.in_buf = b''
