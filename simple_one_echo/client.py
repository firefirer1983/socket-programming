import socket
import time

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect(('127.0.0.1', 5566))
    print('connect success')
    sent = s.send(b'hello world')
    print('sent', sent, ' done')
    while True:
        received = s.recv(1024)
        if not received:
            break
        else:
            print('received:', received)
            time.sleep(1)
            sent = s.send(received)
            print('sent', sent, ' done')
    print('exit')
