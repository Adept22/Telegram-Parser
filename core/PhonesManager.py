import threading
from collections.abc import MutableMapping
from singleton_decorator import singleton

@singleton
class PhonesManager(MutableMapping):
    def __init__(self, *args, **kwargs):
        self._condition = threading.Condition()
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys
        
    def __getitem__(self, key):
        return self.store[self._keytransform(key)]

    def __setitem__(self, key, value):
        with self._condition:
            self.store[self._keytransform(key)] = value
            self._condition.notify_all()

    def __delitem__(self, key):
        with self._condition:
            while not len(self):
                self._condition.wait()
            del self.store[self._keytransform(key)]

    def __iter__(self):
        return iter(self.store)
    
    def __len__(self):
        return len(self.store)

    def _keytransform(self, key):
        return key
