import os
import socket
from collections import Iterable, namedtuple
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


class Question(namedtuple('question', 'qname qtype qclass')):
    pass


class DnsAnswer(namedtuple("DnsAnswer", "name type clz ttl rlength rdata")):
    pass


class Header(namedtuple("Header", "id misc1 misc2 qdcount ancount nscount arcount")):
    pass


class HeaderFieldFactory:
    
    def __call__(self, *args, **kwargs):
        id_ = yield from UnsignedIntegerField(2)
        misc_2 = yield from RawBytesField(1)
        misc_1 = yield from RawBytesField(1)
        qdcount = yield from UnsignedIntegerField(2)
        ancount = yield from UnsignedIntegerField(2)
        nscount = yield from UnsignedIntegerField(2)
        arcount = yield from UnsignedIntegerField(2)
        return Header(id_, misc_2, misc_1, qdcount, ancount, nscount, arcount)


HeaderField = HeaderFieldFactory()


class PointerField:
    pass


class DomainNameFactory:
    
    def __call__(self, offset=None) -> bytes:
        labels = []
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
        yield JumpCursor(pointer)
        domain_name = yield from DomainNameField()
        yield RollBackCursor()
        return domain_name


NameField = NameFieldFactory()


class AnswerFactory:
    
    def __call__(self, ancount):
        answers_ = []
        while ancount:
            name_ = yield from NameField()
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
        print("******************header", header)
        if header.qdcount:
            questions = yield from QuestionField(header.qdcount)
            for q in questions:
                print("******************question", q)
        else:
            questions = []
        if header.ancount:
            answers = yield from AnswerField(header.ancount)
            for ans in answers:
                print("******************answer", ans)
        else:
            answers = []
        if header.arcount:
            authorities = yield from AuthorityField(header.arcount)
        else:
            authorities = []
        
        return header, questions, answers, authorities

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
        header, questions, answers, authorities = rsp.pull(s)
        print(header)
        print(questions)
        print(answers)
        print(authorities)


if __name__ == '__main__':
    main()
