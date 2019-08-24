from sockets5.socks5 import Socks5AuthRsp, Socks5AuthRequest, Socks5AuthMethod, Socks5AddressRequest, \
    Socks5AddressCmd, Socks5AddressAddrType, Socks5AddressRsp
import socket
HOST = "127.0.0.1"
PORT = 1080


def len_gen():
    data = yield 1
    print("data:", data)
    data = yield 2
    print("data:", data)


def data_gen():
    data = None
    lg = len_gen()
    while True:
        try:
            data = yield lg.send(data)
        except StopIteration:
            break


if __name__ == '__main__':
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        s.connect((HOST, PORT))
        s.sendall(Socks5AuthRequest(Socks5AuthMethod.NO_AUTH).to_bytes())
        rsp = Socks5AuthRsp().pull(s)
        print(rsp)

        s.sendall(Socks5AddressRequest(Socks5AddressCmd.CONNECT,
                                       Socks5AddressAddrType.DOMAINNAME,
                                       b"google.com",
                                       80).to_bytes())
        
        rsp = Socks5AddressRsp().pull(s)
        print(rsp)

