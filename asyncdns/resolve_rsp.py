from collections.__init__ import namedtuple

from datafields import UnsignedIntegerField, RawBytesField, I8ArrayField
from utils.util import BackwardCursor, JumpCursor, RollBackCursor


class Question(namedtuple('question', 'qname qtype qclass')):
    pass


class Answer(namedtuple("DnsAnswer", "name type clz ttl rlength rdata")):
    pass


class Header(namedtuple("Header", "id misc1 misc2 qdcount ancount nscount arcount")):
    pass


class HeaderFieldFactory:
    
    def __call__(self):
        id_ = yield from UnsignedIntegerField(2)
        misc_2 = yield from RawBytesField(1)
        misc_1 = yield from RawBytesField(1)
        qdcount = yield from UnsignedIntegerField(2)
        ancount = yield from UnsignedIntegerField(2)
        nscount = yield from UnsignedIntegerField(2)
        arcount = yield from UnsignedIntegerField(2)
        return Header(id_, misc_2, misc_1, qdcount, ancount, nscount, arcount)


HeaderField = HeaderFieldFactory()


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
        if ord(flag) & 0xc0 != 0xc0:
            raise RuntimeError("invalid flag: ", flag)
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
            ans_ = Answer(name_, type_, class_, ttl_, rlength_, rdata_)
            answers_.append(ans_)
            ancount -= 1
        return answers_


AnswerField = AnswerFactory()


class AuthorityField:
    
    def __init__(self, arcount):
        pass


class ResolveResponse:
    
    def __init__(self):
        self._consumer = None
    
    def __call__(self):
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
        
        return header, questions, answers, authorities
