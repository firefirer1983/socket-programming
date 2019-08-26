from utils.util import Consumer


def dns_resolve():
    d = yield 1
    print(d)
    d = yield 2
    print(d)
    d = yield 3
    print(d)


c = Consumer(dns_resolve(), b'\x00\x01\x02\x03\x04\x05\x06')

while True:
    try:
        c.push()
    except StopIteration:
        break
assert c.data == b'\06'
