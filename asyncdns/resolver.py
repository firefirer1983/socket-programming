import socket
from selectors import EVENT_READ, EVENT_WRITE
from threading import RLock

from asyncdns.enums import QType, QClass
from asyncdns.resolve_req import ResolveRequest
from asyncdns.resolve_rsp import ResolveResponse
from eventloop import EventLoop
from exc import DnsRspRecvErr
from lrucache import LRUCache
from utils.util import pull_diagram_sock, pull
from utils.loggers import get_logger

HOST = "8.8.8.8"
PORT = 53
log = get_logger("async-dns")


class Subject:
    def __init__(self, hostname):
        self._obs = []
        self._ip = ""
        self._hostname = hostname
        self._lock = RLock()

    def attach(self, observer):
        if observer not in self._obs:
            with self._lock:
                self._obs.append(observer)

    def detach(self, observer):
        if observer in self._obs:
            with self._lock:
                self._obs.remove(observer)

    @property
    def ip(self):
        return self._ip

    @ip.setter
    def ip(self, value):
        if self._ip != value:
            self._ip = value
            self._notify(self._ip, None)

    def _notify(self, ip, err):
        with self._lock:
            for ob in self._obs:
                ob(ip, err)

    def __del__(self):
        for ob in self._obs:
            ob(None, None)
        self._obs.clear()


class Observer:
    def __init__(self, callback):
        if not callable(callback):
            raise RuntimeError("register observer with an invalid callback")
        self._callback = callback

    def __call__(self, ip, err):
        self._callback(ip, err)


class DnsResolver:
    def __init__(self):
        self._loop = None
        self._hostname_to_callback = dict()
        self._cache = LRUCache(timeout=300.0)
        self._subjects = {}
        self._sock = None

    @staticmethod
    def _make_socket():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.SOL_UDP)
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        return sock

    def add_to_loop(self, loop: EventLoop):
        self._loop = loop
        self._sock = self._make_socket()
        self._loop.add(
            self._sock, EVENT_READ | EVENT_WRITE, self._handle_event
        )
        self._loop.add_periodic(self._periodic_handle)

    def _periodic_handle(self):
        self._cache.sweep()

    def _handle_event(self, sock, mask):
        if mask & EVENT_READ:
            received, addr = sock.recvfrom(1024)
            if addr[0] != HOST:
                return log.info("Unknown server response")
            try:
                if not received:
                    raise DnsRspRecvErr
                header, questions, answers, authorities = pull(
                    ResolveResponse(), received
                )
            except DnsRspRecvErr:
                self._loop.remove(sock)
                self._sock.close()
                self._sock = self._make_socket()
                self._loop.add(
                    self._sock, EVENT_READ | EVENT_WRITE, self._handle_event
                )
            else:
                print(header, questions, answers, authorities)
                for ans in answers:
                    subject_ = self._subjects.get(ans.name, None)
                    if subject_:
                        subject_.ip = ans.rdata

    def close(self):
        self._loop.remove(self._sock)
        self._loop.remove_periodic(self._periodic_handle)
        self._sock.close()
        self._sock = None

    def _send_req(self, hostnames, qtype, qclass):
        self._sock.sendto(
            ResolveRequest(hostnames, qtype, qclass).to_bytes(), (HOST, PORT)
        )

    def resolve(
        self,
        hostnames,
        resolve_callback=None,
        qtype=QType.QTYPE_A,
        qclass=QClass.QCLASS_IN,
    ):
        if isinstance(hostnames, bytes):
            hostnames = [hostnames]
        hostnames = list(
            map(
                lambda h: h.encode("utf8") if isinstance(h, str) else h,
                hostnames,
            )
        )
        for hostname in hostnames:
            print(resolve_callback)
            if resolve_callback and callable(resolve_callback):
                subject_ = self._subjects.get(hostname, None)
                if not subject_:
                    subject_ = Subject(hostname)
                    self._subjects[hostname] = subject_
                subject_.attach(Observer(resolve_callback))
        self._send_req(hostnames, qtype, qclass)


counter = 0


def make_callable():
    def _func(ip, err):
        print("resolve result:")
        print(ip, err)

    return _func


def main():
    assert make_callable() != make_callable()
    loop = EventLoop()
    dns = DnsResolver()
    dns.add_to_loop(loop)
    dns.resolve([b"google.com"], make_callable())
    dns.resolve(b"youtube.com", make_callable())
    loop.run()
    # with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.SOL_UDP) as s:
    #     resolve_req = ResolveRequest([b'www.google.com', b'youtube.com'], QType.QTYPE_A, QClass.QCLASS_IN).to_bytes()
    #     s.sendto(resolve_req, (HOST, PORT))
    #     header, questions, answers, authorities = pull_diagram_sock(ResolveResponse(), s)
    #     log.info(header)
    #     log.info(questions)
    #     log.info(answers)
    #     log.info(authorities)
    
    

if __name__ == "__main__":
    main()
