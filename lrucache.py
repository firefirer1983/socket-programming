import collections
import time
from collections.abc import MutableMapping


class LRUCache(MutableMapping):
    
    def __init__(self, timeout=60.0, close_cb=None, *args, **kwargs):
        self._timeout = timeout
        if not callable(close_cb):
            assert RuntimeError("close call back must be callable")
        self._close_cb = close_cb
        self._last_accesses = collections.deque()
        self._access_keys_by_time = collections.defaultdict(lambda: [])
        self._keys_last_access = {}
        self._lru = {}#.update(*args, **kwargs)
        
    def __getitem__(self, item):
        now_ = time.time()
        self._last_accesses.append(now_)
        self._access_keys_by_time[now_].append(item)
        self._keys_last_access[item] = now_
        return self._lru[item]
    
    def __setitem__(self, key, value):
        now_ = time.time()
        self._last_accesses.append(now_)
        self._access_keys_by_time[now_].append(key)
        self._keys_last_access[key] = now_
        self._lru[key] = value
        
    def __iter__(self):
        return iter(self._lru)
    
    def __len__(self):
        return len(self._lru)
    
    def __delitem__(self, key):
        del self._lru[key]
        del self._keys_last_access[key]
    
    def sweep(self):
        now_ = time.time()
        
        if len(self._last_accesses) == 0:
            return 0
        
        last_access = self._last_accesses[0]
        while self._overdue(last_access, now_):
            self._last_accesses.popleft()
            for k in self._access_keys_by_time[last_access]:
                
                if k in self._lru and self._overdue(self._keys_last_access[k], now_):
                    print(
                        "%s ==> in :%r, overdue:%r" % (
                        k, (k in self._lru), self._overdue(self._keys_last_access[k], now_)))
                    print("del %s" % k)
                    del self._lru[k]
                    del self._keys_last_access[k]
            del self._access_keys_by_time[last_access]
            
            if self._last_accesses:
                last_access = self._last_accesses[0]
            else:
                break
            
    def _overdue(self, access_time, now):
        print("%r vs %r" %(now - access_time, self._timeout))
        return bool(now - access_time > self._timeout)


if __name__ == '__main__':
    c = LRUCache(timeout=0.5)
    c['a'] = 1
    c['b'] = 2
    time.sleep(0.4)
    c.sweep()
    assert c['a'] == 1
    assert c['b'] == 2
    time.sleep(0.5)
    c.sweep()
    assert 'a' not in c
    assert 'b' not in c
