from enum import unique, Enum


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
    TYPE_AAAA = 28


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
    QTYPE_AAAA = 28
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