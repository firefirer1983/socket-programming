import os
import socket
from collections import Iterable
from enum import Enum, unique
import struct

from utils.util import Response, pull_diagram_sock, pull_stream_sock, unpacks, RollBackCursor, JumpCursor, \
    BackwardCursor
from datafields import I8ArrayField, UnsignedIntegerField, RawBytesField

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
        
        self._misc_1 \
            = bits(self._recursion_desired, 1) \
            + bits(self._truncation, 1) \
            + bits(self._auth_answer, 1) \
            + bits(self._opcode, 4) \
            + bits(self._is_response, 1)
        
        self._misc_2 \
            = bits(self._rcode, 4) \
            + bits(self._rsv, 3) \
            + bits(self._recursion_avail, 1)
        
        assert len(self._misc_1) == len(self._misc_2) == 8
        
        self._header = struct.pack(
            '!BBHHHH',
            int(self._misc_2, 2),
            int(self._misc_1, 2),
            self._qdcount,
            self._ancount,
            self._nscount,
            self._arcount)

    def to_bytes(self):
        return self._query_id + self._header


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
        self._address = b''.join(self._address)
    
    def to_bytes(self):
        return self._address


class QueryHeaderSection(HeaderSection):
    def __init__(self, qdcount):
        super().__init__(QueryResponse.QUERY, QueryOpCode.QUERY, 0, qdcount, 0, 0, 0)


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


class Question:
    
    def __init__(self, qname, qtype, qclass):
        self._qname = qname
        self._qtype = qtype
        self._qclass = qclass
    
    @property
    def qname(self):
        return self._qname
    
    @property
    def qtype(self):
        return self._qtype
    
    @property
    def qclass(self):
        return self._qclass
    
    def __str__(self):
        return "<Question %s %u %u>" % (self._qname, self._qtype, self._qclass)


class DnsAnswer:
    
    def __init__(self, name, typ, clz, ttl, rlength, rdata):
        self._name = name
        self._type = typ
        self._class = clz
        self._ttl = ttl
        self._rlength = rlength
        self._rdata = '.'.join([str(byte) for byte in rdata])

    @property
    def name(self):
        return self._name
    
    @property
    def type(self):
        return self._type
    
    @property
    def ttl(self):
        return self._ttl
    
    @property
    def rlength(self):
        return self._rlength
    
    @property
    def rdata(self):
        return self._rdata
    
    def __str__(self):
        return "<Answer name:%s type:%u ttl:%u rlength:%u rdata:%s>" \
               % (self._name, self._type, self._ttl, self._rlength, self._rdata)


class Header:
    
    def __init__(self, *args):
        self._req_id, _, _, self._qdcount, self._ancount, self._nscount, self._arcount = args
    
    @property
    def qdcount(self):
        return self._qdcount
    
    @property
    def ancount(self):
        return self._ancount

    @property
    def nscount(self):
        return self._nscount
    
    @property
    def arcount(self):
        return self._arcount
    
    @property
    def req_id(self):
        return self._req_id

    def __str__(self):
        return "<Header qdcount:%u ancount:%u nscount:%u>" % (
            self.qdcount, self.ancount, self.nscount)


class HeaderFieldFactory:
    
    def __call__(self, *args, **kwargs):
        fmt_ = '!HBBHHHH'
        bytes_ = yield 12
        return Header(*unpacks(fmt_, bytes_))


HeaderField = HeaderFieldFactory()


class PointerField:
    pass


class DomainNameFactory:
    
    def __call__(self, offset=None) -> bytes:
        labels = []
        if offset:
            yield JumpCursor(offset)

        while True:
            
            len_ = yield from UnsignedIntegerField(1)
            if not len_:
                break
            
            data = yield from RawBytesField(len_)
            labels.append(data)
            
        return b'.'.join(labels) if len(labels) else b''


DomainNameField = DomainNameFactory()


class QuestionFactory:
    
    def __call__(self, qdcount):
        questions_ = []
        while qdcount:
            domain_name = yield from DomainNameField()
            qtype = yield from UnsignedIntegerField(2)
            qclass = yield from UnsignedIntegerField(2)
            questions_.append(Question(domain_name, qtype, qclass))
            qdcount -= 1
        return questions_


QuestionField = QuestionFactory()


class NameFieldFactory:
    
    def __call__(self):
        flag = yield from RawBytesField(1)
        assert flag == b'\xc0'
        yield BackwardCursor(1)
        pointer = yield from UnsignedIntegerField(2)
        pointer = int(pointer & 0x3FFF)
        domain_name = yield from DomainNameField(pointer)
        return domain_name


NameField = NameFieldFactory()


class AnswerFactory:
    
    def __call__(self, ancount):
        answers_ = []
        while ancount:
            name_ = yield from NameField()
            yield RollBackCursor()
            type_ = yield from UnsignedIntegerField(2)
            class_ = yield from UnsignedIntegerField(2)
            ttl_ = yield from UnsignedIntegerField(4)
            rlength_ = yield from UnsignedIntegerField(2)
            rdata_ = yield from I8ArrayField(rlength_)
            ans_ = DnsAnswer(name_, type_, class_, ttl_, rlength_, rdata_)
            answers_.append(ans_)
            ancount -= 1
        return answers_


AnswerField = AnswerFactory()


class AuthorityField:
    
    def __init__(self, arcount):
        pass


class ResolveResponse(Response):
    
    def __init__(self):
        self._consumer = None
    
    def __call__(self, *args, **kwargs):
        header = yield from HeaderField()
        if header.qdcount:
            questions = yield from QuestionField(header.qdcount)
        else:
            questions = []
        if header.ancount:
            answers = yield from AnswerField(header.ancount)
        else:
            answers = []
        if header.arcount:
            authorities = yield from AuthorityField(header.arcount)
        else:
            authorities = []
            
        return dict(
            header=header,
            questions=questions,
            answers=answers,
            authorities=authorities
        )

    def pull(self, sock):
        return pull_diagram_sock(self, sock)


class DNSResolver:
    
    def __init__(self):
        pass


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.SOL_UDP) as s:
        resolve_req = ResolveRequest([b'www.google.com'], QType.QTYPE_A).to_bytes()
        s.sendto(resolve_req, (HOST, PORT))
        rsp = ResolveResponse()
        dns_result = rsp.pull(s)
        for k, vs in dns_result.items():
            print("%s:" % k)
            if isinstance(vs, Iterable):
                for v in vs:
                    print("%s" % v)
            else:
                print("%s" % vs)


if __name__ == '__main__':
    main()
