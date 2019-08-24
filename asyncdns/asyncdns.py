import os
import socket
from collections import Iterable
from enum import Enum, unique
import struct

HOST = "8.8.8.8"
PORT = 53


@unique
class Type(Enum):
    TYPE_A = 1
    TYPE_NS = 2
    TYPE_MD = 3
    TYPE_MF = 4
    TYPE_CNAME = 5
    TYPE_NULL = 10
    TYPE_PTR = 12
    TYPE_MX = 15


@unique
class QType(Enum):
    QTYPE_A = 1
    QTYPE_NS = 2
    QTYPE_MD = 3
    QTYPE_MF = 4
    QTYPE_CNAME = 5
    QTYPE_NULL = 10
    QTYPE_PTR = 12
    QTYPE_MX = 15
    QTYPE_ALL = 255


@unique
class Class(Enum):
    CLASS_IN = 1
    CLASS_CS = 2
    CLASS_CH = 3
    CLASS_HS = 4


@unique
class QClass(Enum):
    QCLASS_IN = 1
    QCLASS_CS = 2
    QCLASS_CH = 3
    QCLASS_HS = 4
    QCLASS_ALL = 255


@unique
class QueryOpCode(Enum):
    QUERY = 0
    IQUERY = 1
    STATUS = 2
    RSV = 3


@unique
class ResponseCode(Enum):
    NO_ERR = 0
    FMT_ERR = 1
    SRV_ERR = 2
    NAME_ERR = 3
    NOT_IMPL = 4
    REFUSED = 5


@unique
class QueryResponse(Enum):
    QUERY = 0
    RESPONSE = 1


def _bin(s):
    return str(s) if s <= 1 else _bin(s >> 1) + str(s & 1)


def bits(s, cnt):
    s = _bin(int(s))
    pad = cnt - len(s)
    if pad > 0:
        s = '0' * pad + s
    return s


class HeaderSection:
    
    def __init__(self, is_query, opcode, rcode, qdcount, ancount, nscount, arcount):
        self._query_id = os.urandom(2)
        self._is_response = not is_query
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
        self._misc = bits(self._is_response, 1) \
            + bits(self._opcode, 4) \
            + bits(self._auth_answer, 1) \
            + bits(self._truncation, 1) \
            + bits(self._recursion_desired, 1) \
            + bits(self._recursion_avail, 1) \
            + bits(self._rsv, 3) + bits(self._rcode, 4)
        
        assert len(self._misc) == 16
        self._header = self._query_id + struct.pack('>HHHHH',
                                                    int(self._misc, 2),
                                                    self._qdcount,
                                                    self._ancount,
                                                    self._nscount,
                                                    self._arcount)
    
    def to_bytes(self):
        return self._header


class ResolveRequestAddress:
    
    def __init__(self, address):
        self._address = []
        address = address.strip(b'.')
        labels = address.split(b'.')
        for label in labels:
            len_ = len(label)
            if len_ > 63:
                self._address = None
                return
            self._address.append(bytes(chr(len_), 'utf8'))
            self._address.append(label)
        self._address.append(b'\0')
        print(self._address)
        self._address = b''.join(self._address)
    
    def to_bytes(self):
        print("address", self._address)
        return self._address


class QueryHeaderSection(HeaderSection):
    def __init__(self, qdcount):
        super().__init__(True, QueryOpCode.QUERY, qdcount, 0, 0, 0, 0)


class ResolveRequest:
    
    def __init__(self, addresses, qtype):
        if not isinstance(addresses, Iterable):
            addresses = [addresses]
        self._qtype = qtype
        self._header = QueryHeaderSection(len(addresses))
        self._addresses = [ResolveRequestAddress(address) for address in addresses]
        self._qtype = qtype.value
        self._qclass = QClass.QCLASS_IN.value
    
    def to_bytes(self):
        addresses = b''
        for address in self._addresses:
            addresses += address.to_bytes()
        return self._header.to_bytes() \
            + addresses \
            + struct.pack('>H', self._qtype) \
            + struct.pack('>H', self._qclass)


class DNSResolver:
    
    def __init__(self):
        pass


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.SOL_UDP) as s:
        resolve_req = ResolveRequest([b'www.google.com'], QType.QTYPE_A)
        s.sendto(resolve_req.to_bytes(), (HOST, PORT))
        resolved_, addr = s.recvfrom(1024)
        print("resolved:", resolved_)
        print("addr:", addr)


if __name__ == '__main__':
    main()
