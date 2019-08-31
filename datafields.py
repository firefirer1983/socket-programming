from utils.util import unpacks


class I8ArrayFactory:
    
    def __call__(self, length):
        fmt_ = '!' + 'B'*length
        bytes_ = yield length
        return unpacks(fmt_, bytes_)


I8ArrayField = I8ArrayFactory()


class UnsignedIntegerFactory:
    
    def __call__(self, length):
        if length == 1:
            fmt_ = '!B'
        elif length == 2:
            fmt_ = '!H'
        elif length == 4:
            fmt_ = '!I'
        elif length == 8:
            fmt_ = '!Q'
        else:
            raise RuntimeError("Integer length is out of range")
        bytes_ = yield length
        return unpacks(fmt_, bytes_)


UnsignedIntegerField = UnsignedIntegerFactory()


class StringFactory:
    
    def __call__(self, length):
        fmt_ = '!%us' % length
        bytes_ = yield length
        return unpacks(fmt_, bytes_)


StringField = StringFactory()


class RawBytesFactory:
    
    def __call__(self, length) -> bytes:
        bytes_ = yield length
        return bytes_


RawBytesField = RawBytesFactory()


class UndefinedField:
    pass


