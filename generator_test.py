class TestGen:
    
    def __init__(self, cnt):
        self._cnt = cnt
        
    def __call__(self, *args, **kwargs):
        dat_ = 1
        while True:
            try:
                dat_ = yield dat_
                if dat_ == 20:
                    raise StopIteration
            except StopIteration:
                break

    def pull(self):
        dat_ = None
        g = self()
        while True:
            try:
                dat_ = g.send(dat_)
            except StopIteration:
                break
            else:
                dat_ += 1
        return dat_


if __name__ == '__main__':
    tg = TestGen(20)
    print(tg.pull())
