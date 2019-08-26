import os
import socket
from collections import Iterable
from enum import Enum, unique
import struct

from utils.util import Data, Response, pull_diagram_sock, pull_stream_sock, unpacks

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
        print("misc_1", int(self._misc_1, 2))
        print("misc_2", int(self._misc_2, 2))
        
        self._header = struct.pack(
            '!BBHHHH',
            int(self._misc_2, 2),
            int(self._misc_1, 2),
            self._qdcount,
            self._ancount,
            self._nscount,
            self._arcount)

    def to_bytes(self):
        print("req_id:%r" % self._query_id)
        print("header:%r" % self._header)
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
        print(self._address)
        self._address = b''.join(self._address)
    
    def to_bytes(self):
        print("address", self._address)
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


class HeaderField(Data):
    
    def __init__(self):
        super().__init__(12)
        self._fmt = '!HBBHHHH'
    
    def __call__(self, *args, **kwargs):
        self._bytes = yield self._length
        print("header bytes: ", self._bytes)
        return Header(*unpacks(self._fmt, self._bytes))


class PointerField(Data):
    pass


class DomainNameField(Data):
    
    def __init__(self, offset):
        self._length = 0
        self._labels = []
        self._offset = offset
        super().__init__(self._length)
    
    def __call__(self) -> bytes:
        
        if self._offset:
            data = yield (self._offset, 1)
        else:
            data = yield 1
        while True:
            
            len_ = unpacks('!B', data)
            if not len_:
                break
            
            data = yield len_
            self._labels.append(data)
            
            data = yield 1
        return b'.'.join(self._labels)


class IPField(Data):
    def __init__(self, offset):
        self._length = 0
        self._offset = offset
        super().__init__(self._length)
    
    def __call__(self) -> bytes:
        
        if self._offset:
            data = yield (self._offset, 1)
        else:
            data = yield 1
        while True:
            
            len_ = unpacks('!B', data)
            if not len_:
                break
            
            data = yield len_
            self._bytes += data
            
            data = yield 1
        return self._bytes


class Question:
    
    def __init__(self, qname: bytes, qtype, qclass):
        self._qname = unpacks("!%us" % len(qname), qname)
        self._qtype = unpacks("!H", qtype)
        self._qclass = unpacks("!H", qclass)
    
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
        self._name = unpacks("!%us" % len(name), name)
        self._type = unpacks("!H", typ)
        self._class = unpacks("!H", clz)
        self._ttl = unpacks("!I", ttl)
        self._rlength = unpacks("!H", rlength)
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


class QuestionField(Data):
    
    def __init__(self, qdcount):
        self._cnt = qdcount
        self._length = 0
        self._questions = []
        super().__init__(self._length)
    
    def __call__(self, *args, **kwargs):
        while self._cnt:
            field = DomainNameField(0)
            domain_name = yield from field()
            qtype = yield 2
            qclass = yield 2
            print("%u: %r %r %r" % (self._cnt, domain_name, qtype, qclass))
            self._questions.append(Question(domain_name, qtype, qclass))
            self._cnt -= 1
        return self._questions


class NameField(Data):
    
    def __init__(self):
        self._length = 0
        super().__init__(self._length)
    
    def __call__(self):
        length = yield 1
        assert length == b'\xc0'
        length += yield 1
        pointer = unpacks("!H", length)
        pointer = int(pointer & 0x3FFF)
        field = DomainNameField(pointer)
        domain_name = yield from field()
        return domain_name


class AnswerField(Data):
    
    def __init__(self, ancount):
        self._cnt = ancount
        self._answers = []
        self._labels = []
        self._length = 0
        super().__init__(self._length)
    
    def __call__(self, *args, **kwargs):
        while self._cnt:
            field = NameField()
            name_ = yield from field()
            _ = yield -1, 1
            type_ = yield 2
            class_ = yield 2
            ttl_ = yield 4
            rlength_ = yield 2
            rdata_ = yield unpacks('!H', rlength_)
            ans_ = DnsAnswer(name_, type_, class_, ttl_, rlength_, rdata_)
            self._answers.append(ans_)
            self._cnt -= 1
        for ans in self._answers:
            print(str(ans))
        return self._answers


class AuthorityField:
    
    def __init__(self, arcount):
        pass


class ResolveResponse(Response):
    
    def __init__(self):
        self._consumer = None
    
    def fields_gen(self):
        ret_ = dict()
        header = yield ("header", HeaderField())
        print("qdcount:%u ancount:%u arcount:%u" % (header.qdcount, header.ancount, header.arcount))
        if header.qdcount:
            ret_["questions"] = yield ("question", QuestionField(header.qdcount))
        if header.ancount:
            ret_["answers"] = yield ("answer", AnswerField(header.ancount))
        if header.arcount:
            ret_["authorities"] = yield ("authority", AuthorityField(header.arcount))
        return ret_
    
    def __call__(self, *args, **kwargs):
        fields = self.fields_gen()
        dat = None
        while True:
            field_name, field = fields.send(dat)
            dat = yield from field()
    
    def pull(self, sock):
        return pull_diagram_sock(self, sock)


class DNSResolver:
    
    def __init__(self):
        pass


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.SOL_UDP) as s:
        resolve_req = ResolveRequest([b'www.google.com'], QType.QTYPE_A).to_bytes()
        print("req:%r" % resolve_req)
        s.sendto(resolve_req, (HOST, PORT))
        rsp = ResolveResponse()
        dns_result = rsp.pull(s)
        for k, vs in dns_result.items():
            print("%s:" % k)
            for v in vs:
                print("%s" % v)


if __name__ == '__main__':
    main()
