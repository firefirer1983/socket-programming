from functools import partial
import asyncio
from asyncdns.enums import QType, QClass
from asyncdns.resolve_req import ResolveRequest
from asyncdns.resolve_rsp import ResolveResponse
from concurrent.futures import ThreadPoolExecutor
from lrucache import LRUCache
from utils.util import pull
import socket


HOST = "8.8.8.8"
PORT = 53


pool = ThreadPoolExecutor(max_workers=10)


class DnsResolver:
    def __init__(self, loop, host, port):
        self._loop = loop
        self._host = host
        self._port = port
        self._hostname_to_callback = dict()
        self._cache = LRUCache(timeout=300.0)
        self._subjects = {}
        self._sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.SOL_UDP
        )
        # self._sock.setblocking(False)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

    def _resolve(self, hostnames, qtype, qclass):
        if isinstance(hostnames, bytes):
            hostnames = [hostnames]
        hostnames = list(
            map(
                lambda h: h.encode("utf8") if isinstance(h, str) else h,
                hostnames,
            )
        )
        resolve_req = ResolveRequest(hostnames, qtype, qclass).to_bytes()
        print("resolve_req:", resolve_req)
        self._sock.sendto(resolve_req, (self._host, self._port))
        print("sendto done")
        received, addr = self._sock.recvfrom(1024)
        print("received:", received, "addr:", addr)
        if addr != (HOST, PORT):
            return None
        # received = await self._loop.sock_recv(self._sock, 1024)
        # print("received:", received, "addr:", addr)
        header, questions, answers, authorities = pull(
            ResolveResponse(), received
        )
        return answers

    async def resolve(
        self, hostnames, qtype=QType.QTYPE_A, qclass=QClass.QCLASS_IN
    ):

        answers = await self._loop.run_in_executor(
            pool, partial(self._resolve, hostnames, qtype, qclass)
        )
        return answers[0] if answers else None


if __name__ == "__main__":
    mloop = asyncio.get_event_loop()
    dns = DnsResolver(mloop, HOST, PORT)
    f = dns.resolve(b"google.com")
    ret = mloop.run_until_complete(f)
    print(ret)
