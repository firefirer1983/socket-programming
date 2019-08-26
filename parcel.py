
class Consumer:
    
    def __init__(self, g, data):
        self._pipe = g
        self._wait_for = next(g)
        self._offset = 0
        self._bytes = data
    
    @property
    def wait_for(self):
        return self._wait_for
    
    @property
    def offset(self):
        return self._offset
    
    def push(self):
        to_send = self._bytes[self._offset:self._offset + self._wait_for]
        self._offset += self._wait_for
        self._wait_for = self._pipe.send(to_send)
    
    @property
    def data(self):
        return self._bytes[self._offset:self._offset + self._wait_for]
    

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
