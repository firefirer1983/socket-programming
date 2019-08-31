from enum import unique, Enum

DST_ADDR = b"google.com"
DST_PORT = 80
VER = 5
CONNECT_CMD = 1
IP4_ATYP = 3


@unique
class Socks5AddressCmd(Enum):
    CONNECT = 0x01
    BIND = 0x02
    UDP_ASSOCIATE = 0x04


@unique
class Socks5AddressAddrType(Enum):
    IP4 = 0x01
    DOMAINNAME = 0x03
    IP6 = 0x04


@unique
class Socks5AuthMethod(Enum):
    NO_AUTH = 0x00
    GSSAPI = 0x01
    USRNAME_PWD = 0x02
    IANA_ASSIGNED = 0x03
    PRIVATE_RSV = 0x80
    NO_ACCEPTABLE = 0xFF


@unique
class Socks5RepType(Enum):
    
    SUCCEEDED = 0x00
    GENERAL_SOCKS_SERVER_FAILURE = 0x01
