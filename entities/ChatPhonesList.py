import logging
import multiprocessing
from collections.abc import MutableSequence

import globalvars, entities

class ChatPhonesList(MutableSequence):
    def __init__(self, _list: 'list[entities.TypeChatPhone]' = [], *args, **kwargs):
        self._condition = multiprocessing.Condition()

        self._list = _list

    def __repr__(self) -> 'str':
        return "<{0} {1}>".format(self.__class__.__name__, self._list)

    def __str__(self) -> 'str':
        return str(self._list)
        
    def __getitem__(self, i) -> 'entities.TypeChatPhone':
        return self._list[i]

    def __setitem__(self, i, value: 'entities.TypeChatPhone') -> 'None':
        with self._condition:
            self._list[i] = value

            self._condition.notify_all()

    def __delitem__(self, i) -> 'None':
        del self._list[i]

    def __iter__(self) -> 'entities.TypeChatPhone':
        with self._condition:
            while not len(self):
                self._condition.wait()
            
            return iter(self._list)
    
    def __len__(self) -> 'int':
        return len(self._list)

    def index(self, value: 'entities.TypeChatPhone') -> 'int':
        for i, item in enumerate(self._list):
            if item.id == value.id:
                return i
        else:
            raise ValueError("item not found")

    def insert(self, i, value: 'entities.TypeChatPhone') -> 'None':
        self._list.insert(i, value)

    def append(self, value: 'entities.TypeChatPhone') -> 'None':
        with self._condition:
            if value.id not in [i.id for i in self._list]:
                self._list.append(value)

            self._condition.notify_all()

    def remove(self, value: 'entities.TypeChatPhone') -> 'None':
        del self._list[self.index(value)]
