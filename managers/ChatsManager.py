from multiprocessing.managers import NamespaceProxy
from collections.abc import MutableMapping
# from singleton_decorator import singleton

import entities

class ChatsManager(MutableMapping):
    def __init__(self, *args, **kwargs):
        self.store = dict()
        self.update(dict(*args, **kwargs))  # use the free update to set keys
        
    def __getitem__(self, key) -> 'entities.TypeChat':
        return self.store[self._keytransform(key)]

    def __setitem__(self, key, value: 'entities.TypeChat'):
        self.store[self._keytransform(key)] = value

    def __delitem__(self, key):
        del self.store[self._keytransform(key)]

    def __iter__(self):
        return iter(self.store)
    
    def __len__(self):
        return len(self.store)

    def _keytransform(self, key):
        return key

class ChatsManagerProxy(NamespaceProxy):
    _exposed_ = ('__getattribute__', '__setattr__', '__delattr__')