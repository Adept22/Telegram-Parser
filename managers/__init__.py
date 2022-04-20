import multiprocessing
from multiprocessing.managers import BaseManager, DictProxy

class ParserManager(BaseManager):
    pass

class LockableDictProxy(DictProxy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._condition = multiprocessing.Condition()
        
    def __getitem__(self, *args):
        with self._condition:
            while not self._callmethod('__len__'):
                self._condition.wait()
            
            return self._callmethod('__getitem__', args)

    def __setitem__(self, *args):
        with self._condition:
            _item = self._callmethod('__setitem__', args)

            self._condition.notify_all()

            return _item

    def __delitem__(self, *args):
        return self._callmethod('__delitem__', args)

    def __iter__(self):
        with self._condition:
            while not self._callmethod('__len__'):
                self._condition.wait()
            
            return self._callmethod('__iter__')

    def __len__(self):
        return self._callmethod('__len__')

ParserManager.register('dict', dict, LockableDictProxy)