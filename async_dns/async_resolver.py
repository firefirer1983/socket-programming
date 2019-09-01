import asyncio

from asyncdns.enums import QType, QClass
from asyncdns.resolve_req import ResolveRequest
from asyncdns.resolve_rsp import ResolveResponse
from utils.util import pull

HOST = "8.8.8.8"
PORT = 53


class DnsProtocol:
    
    def __init__(self, loop):
        self._loop = loop
        self._transport = None
        self._on_resolve = loop.create_future()
        self._on_lost = loop.create_future()
        self._answers = None
    
    def connection_made(self, transport):
        print("connected")
        self._transport = transport

    def datagram_received(self, data, addr):
        if addr != (HOST, PORT):
            print("received:", data)
            return None
        else:
            header, questions, answers, authorities = pull(
                ResolveResponse(), data
            )
            self._answers = answers
            self._on_resolve.set_result(self._answers)

    def error_received(self, exc):
        print("Error received", exc)
        
    def connection_lost(self, exc):
        print("connection lost")
        self._on_lost.set_result(True)
        
    def resolve(self, hostnames, qtype=QType.QTYPE_A, qclass=QClass.QCLASS_IN):
        if isinstance(hostnames, bytes):
            hostnames = [hostnames]
        else:
            hostnames = [h.encode("utf8") for h in hostnames]
        req = ResolveRequest(hostnames, qtype, qclass).to_bytes()
        self._transport.sendto(req)
        
    @property
    def resolved(self):
        return self._on_resolve

    @property
    def on_lost(self):
        return self._on_lost
    

async def main(loop):
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: DnsProtocol(loop),
        remote_addr=(HOST, PORT))
    
    try:
        protocol.resolve(b"google.com")
        resolved = await protocol.resolved
        protocol.resolve(b"pornhub.com")
        resolved = await protocol.resolved
        print(resolved)
        lost = await protocol.on_lost
        print(lost)
    finally:
        transport.close()


if __name__ == '__main__':
    mloop = asyncio.get_event_loop()
    mloop.run_until_complete(main(mloop))
