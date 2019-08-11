import socket
import selectors
import types

select = selectors.DefaultSelector()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setblocking(False)
    s.connect_ex(('127.0.0.1', 5566))
    select.register(s,
                    selectors.EVENT_READ | selectors.EVENT_WRITE,
                    data=types.SimpleNamespace(
                        in_buf=b'',
                        out_buf=b'hello world'
                    ))
    
    while True:
        events = select.select(timeout=None)
        for key, mask in events:
            if mask & selectors.EVENT_WRITE and key.data.out_buf:
                sent = s.send(key.data.out_buf[:11])
                print('sent:', sent)
                key.data.out_buf = key.data.out_buf[sent:]
            
            if mask & selectors.EVENT_READ:
                received = s.recv(1024)
                if not received:
                    break
                key.data.in_buf = key.data.in_buf + received
            
            if key.data.in_buf:
                key.data.out_buf += key.data.in_buf
                key.data.in_buf = b''
