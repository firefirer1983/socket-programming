from utils.util import Pool


def dns_resolve():
    d = yield 1
    print(d)
    d = yield 2
    print(d)
    d = yield 3
    print(d)


c = Pool(dns_resolve(), b'\x00\x01\x02\x03\x04\x05\x06')

while True:
    try:
        c.pump()
    except StopIteration:
        break
assert c.data == b'\06'
