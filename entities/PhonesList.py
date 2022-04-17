import multiprocessing
from collections.abc import MutableSequence

import entities
from services.PhonesManager import PhonesManager

class PhonesList(MutableSequence):
    def __init__(self, _list: 'list[dict]' = [], *args, **kwargs):
        self._condition = multiprocessing.Condition()

        self._list = [PhonesManager()[p['id']] for p in _list if p['id'] in PhonesManager()]

    def __repr__(self) -> 'str':
        return "<{0} {1}>".format(self.__class__.__name__, self._list)

    def __str__(self) -> 'str':
        return str(self._list)
        
    def __getitem__(self, i) -> 'entities.TypePhone':
        return self._list[i]

    def __setitem__(self, i, value: 'entities.TypePhone') -> 'None':
        with self._condition:
            self._list[i] = value

            self._condition.notify_all()

    def __delitem__(self, i) -> 'None':
        del self._list[i]

    def __iter__(self) -> 'entities.TypePhone':
        with self._condition:
            while not len(self):
                self._condition.wait()
            
            return iter(self._list)
    
    def __len__(self) -> 'int':
        return len(self._list)

    def index(self, value: 'entities.TypePhone') -> 'int':
        for i, item in enumerate(self._list):
            if item.id == value.id:
                return i
        else:
            raise ValueError("item not found")

    def insert(self, i, value: 'entities.TypePhone') -> 'None':
        self._list.insert(i, value)

    def append(self, value: 'entities.TypePhone') -> 'None':
        if not value.id in PhonesManager():
            raise ValueError(f"Phone {value} does not exist in manager.")

        if value.id not in [i.id for i in self._list]:
            self._list.append(value)

    def remove(self, value: 'entities.TypePhone') -> 'None':
        del self._list[self.index(value)]
