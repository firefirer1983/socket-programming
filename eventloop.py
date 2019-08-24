# When will my application receive SIGPIPE?
# From Richard Stevens ( rstevens@noao.edu):
#
# Very simple: with TCP you get SIGPIPE if your end of the connection has received an RST from the other end.
# What this also means is that if you were using select instead of write, the select would have indicated the socket
# as being readable, since the RST is there for you to read (read will return an error with errno set to ECONNRESET).
#
# Basically an RST is TCP's response to some packet that it doesn't expect and has no other way of dealing with.
# A common case is when the peer closes the connection (sending you a FIN) but you ignore it because you're writing
# and not reading. (You should be using select.) So you write to a connection that has been closed by the other end and
# the other end's TCP responds with an RST.

import sys
import errno
import selectors
import time
import logging

verbose = True

log = logging.getLogger('eventloop')
log.addHandler(logging.StreamHandler(sys.stdout))

TIMEOUT_PRECISION = 10


def current_ts():
    return time.time()


def errno_from_except(e):
    if hasattr(e, 'errno'):
        return e.errno
    elif e.args:
        return e.args[0]
    else:
        return None


def print_exec(e):
    global verbose
    log.error(e)
    if verbose:
        log.exception(e)
        
    
class EventLoop:
    
    def __init__(self):
        self._select = selectors.DefaultSelector()
        self._last_time = current_ts()
        self._periodic_callbacks = []
        self._stopping = False
        
    def poll(self, timeout):
        events = self._select.select(timeout=timeout)
        return [(key.fileobj, key.raw_bytes, mask) for key, mask in events]
    
    def add(self, f, mode, handler):
        self._select.register(f, mode, handler)
    
    def remove(self, f):
        self._select.unregister(f)
        
    def add_periodic(self, callback):
        if callable(callback):
            self._periodic_callbacks.append(callback)
            return True
        return False
        
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
                events = self.poll(TIMEOUT_PRECISION)
            except (OSError, IOError) as e:
                if errno_from_except(e) in (errno.EPIPE, errno.EINTR):
                    asap = True
                else:
                    print_exec(e)
                    continue
            else:
                for fileobj, handler, mask in events:
                    if handler and callable(handler):
                        try:
                            handler(fileobj, mask)
                        except (OSError, IOError) as e:
                            print_exec(e)
            now = current_ts()

            if asap or now - self._last_time > TIMEOUT_PRECISION:
                for callback in self._periodic_callbacks:
                    if callback and callable(callback):
                        callback()
                self._last_time = now
    
    def __del__(self):
        self.stop()
        self._select.close()
