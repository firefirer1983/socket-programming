import socket
import selectors
import time


def current_ts():
    return time.time()


TIMEOUT_PRECISION = 10


class EventLoop:
    
    def __init__(self):
        self._select = selectors.DefaultSelector()
        self._last_time = current_ts()
        self._periodic_callbacks = []
        self._stopping = False
        
    def poll(self, timeout):
        key, mask = self._select.select(timeout=timeout)
        return key.fileobj, key.data, mask
    
    def add(self, f, mode, handler):
        self._select.register(f, mode, handler)
    
    def remove(self, f):
        self._select.unregister(f)
        
    def add_periodic(self, callback):
        self._periodic_callbacks.append(callback)
        
    def remove_periodic(self, callback):
        self._periodic_callbacks.remove(callback)
        
    def modify(self, f, mode):
        self._select.unregister(f)
        self._select.register(f, mode)
        
    def stop(self):
        self._stopping = True
        
    def run(self):
        while not self._stopping:
            asap = False
            try:
                fileobj, handler, mask = self.poll(TIMEOUT_PRECISION)
            except (OSError, IOError) as e:
                asap = True
            else:
                if handler and callable(handler):
                    try:
                        handler(fileobj, mask)
                    except (OSError, IOError) as e:
                        pass
            now = current_ts()

            if asap or now - self._last_time > TIMEOUT_PRECISION:
                for callback in self._periodic_callbacks:
                    if callback and callable(callback):
                        callback()
                self._last_time = now
