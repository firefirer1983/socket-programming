import os
import struct
from typing import Iterable

from asyncdns.enums import QueryOpCode, QueryResponse
from utils.util import bits


class HeaderSection:
    def __init__(self, qr, opcode, rcode, qdcount, ancount, nscount, arcount):
        self._query_id = os.urandom(2)
        self._is_response = qr.value
        self._opcode = opcode.value
        self._auth_answer = False
        self._truncation = False
        self._recursion_desired = False
        self._recursion_avail = False
        self._rsv = 0
        self._rcode = rcode
        self._qdcount = qdcount
        self._ancount = ancount
        self._nscount = nscount
        self._arcount = arcount

        self._misc_1 = (
            bits(self._recursion_desired, 1)
            + bits(self._truncation, 1)
            + bits(self._auth_answer, 1)
            + bits(self._opcode, 4)
            + bits(self._is_response, 1)
        )

        self._misc_2 = (
            bits(self._rcode, 4)
            + bits(self._rsv, 3)
            + bits(self._recursion_avail, 1)
        )

        assert len(self._misc_1) == len(self._misc_2) == 8

        self._header = struct.pack(
            "!BBHHHH",
            int(self._misc_2, 2),
            int(self._misc_1, 2),
            self._qdcount,
            self._ancount,
            self._nscount,
            self._arcount,
        )

    def to_bytes(self):
        return self._query_id + self._header


class ResolveRequestAddress:
    def __init__(self, address):
        self._address = []
        address = address.strip(b".")
        labels = address.split(b".")
        for label in labels:
            len_ = len(label)
            if len_ > 63:
                self._address = None
                return
            self._address.append(bytes(chr(len_), "utf8"))
            self._address.append(label)
        self._address.append(b"\0")
        self._address = b"".join(self._address)

    def to_bytes(self):
        return self._address


class QueryHeaderSection(HeaderSection):
    def __init__(self, qdcount):
        super().__init__(
            QueryResponse.QUERY, QueryOpCode.QUERY, 0, qdcount, 0, 0, 0
        )


class ResolveRequest:
    def __init__(self, addresses, qtype, qclass):
        if not isinstance(addresses, Iterable):
            addresses = [addresses]
        self._header = QueryHeaderSection(len(addresses))
        self._addresses = [
            ResolveRequestAddress(address) for address in addresses
        ]
        self._qtype = qtype.value
        self._qclass = qclass.value

    def to_bytes(self):
        addresses = b""
        for address in self._addresses:
            addresses += address.to_bytes()
        return (
            self._header.to_bytes()
            + addresses
            + struct.pack(">H", self._qtype)
            + struct.pack(">H", self._qclass)
        )
