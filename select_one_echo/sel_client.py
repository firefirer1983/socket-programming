import socket
import selectors
import types


counter = 0

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
            if mask & selectors.EVENT_WRITE and key.raw_bytes.out_buf:
                try:
                    sent = s.send(key.raw_bytes.out_buf[:11])
                except BlockingIOError:
                    continue
                except ConnectionResetError:
                    s.close()
                    select.unregister(s)
                    continue
                print('sent:', sent)
                counter += 1
                key.raw_bytes.out_buf = key.raw_bytes.out_buf[sent:]
            
            if mask & selectors.EVENT_READ:
                try:
                    received = s.recv(1024)
                except BlockingIOError:
                    continue
                except ConnectionResetError:
                    s.close()
                    select.unregister(s)
                    continue
                if not received:
                    break
                key.raw_bytes.in_buf = key.raw_bytes.in_buf + received
            
            if key.raw_bytes.in_buf:
                key.raw_bytes.out_buf += key.raw_bytes.in_buf
                key.raw_bytes.in_buf = b''
        
        if counter > 100000:
            break
        

