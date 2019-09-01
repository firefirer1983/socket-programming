import asyncio
from asyncdns.enums import QType, QClass
from asyncdns.resolve_req import ResolveRequest
from asyncdns.resolve_rsp import ResolveResponse
from lrucache import LRUCache
from utils.util import pull
import socket


HOST = "8.8.8.8"
PORT = 53


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
        self._sock.setblocking(False)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

    async def _resolve(self, hostnames, qtype, qclass):
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
        await self._loop.sock_recv(self._sock, 1)
        received, addr = self._sock.recvfrom(1024)
        # received, addr = self._sock.recvfrom(1)
        # print("received:", received, "addr:", addr)
        # if addr != (HOST, PORT):
        #     return None
        # received = await self._loop.sock_recv(self._sock, 1024)
        # print("received:", received, "addr:", addr)
        header, questions, answers, authorities = pull(
            ResolveResponse(), received
        )
        return answers

    def resolve(self, hostnames, qtype=QType.QTYPE_A, qclass=QClass.QCLASS_IN):
        return self._loop.create_task(self._resolve(hostnames, qtype, qclass))


if __name__ == "__main__":
    mloop = asyncio.get_event_loop()
    dns = DnsResolver(mloop, HOST, PORT)
    f = dns.resolve(b"google.com")
    mloop.run_until_complete(f)
    print(f.result())
