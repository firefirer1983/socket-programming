import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(('127.0.0.1', 5566))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    s.listen(10)
    csock, address = s.accept()
    print("connected:", address)
    with csock:
        while True:
            read_buf = csock.recv(1024)
            if not read_buf:
                print('received CLOSE')
                break
            else:
                print('received :', read_buf)
                sent = csock.send(read_buf)
                print('sent', sent, ' done')
    print('exit')
