from functools import wraps


def exception_handle(self_):
    def catcher(func_):
        if self_:
            @wraps(func_)
            def wrapper(self, *args, **kwargs):
                try:
                    return func_(self, *args, **kwargs)
                except Exception as e:
                    print(e)
                    return None
        else:
            @wraps(func_)
            def wrapper(*args, **kwargs):
                try:
                    return func_(*args, **kwargs)
                except Exception as e:
                    print(e)
                    return None
        return wrapper
    
    return catcher


class Testing:
    
    @exception_handle(self_=True)
    def test_raise_runtime_err(self):
        raise RuntimeError("I am caught!")


@exception_handle(self_=False)
def main():
    testing = Testing()
    testing.test_raise_runtime_err()
    raise RuntimeError("I am caught too!")


if __name__ == '__main__':
    main()
