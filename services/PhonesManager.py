import multiprocessing
from collections.abc import MutableMapping
# from singleton_decorator import singleton

class PhonesManager(MutableMapping):
    def __init__(self, *args, **kwargs):
        self._condition = multiprocessing.Condition()

        self.store = dict()

        self.update(dict(*args, **kwargs))  # use the free update to set keys
        
    def __getitem__(self, key):
        with self._condition:
            while not len(self):
                self._condition.wait()
            
            return self.store[key]

    def __setitem__(self, key, value):
        with self._condition:
            self.store[key] = value

            self._condition.notify_all()

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        with self._condition:
            while not len(self):
                self._condition.wait()
            
            return iter(self.store)
    
    def __len__(self):
        return len(self.store)
