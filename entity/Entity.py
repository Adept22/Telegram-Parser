from abc import ABC, abstractmethod

import exceptions
from services import ApiService

class Entity(ABC):
    def __init__(self) -> None:
        pass

    @property
    @abstractmethod
    def name(self) -> 'str':
        pass

    @property
    @abstractmethod
    def unique_constraint(self) -> 'dict':
        pass

    @abstractmethod
    def serialize(self) -> 'dict':
        pass

    @abstractmethod
    def deserialize(self, _dict: 'dict') -> 'Entity':
        pass

    def save(self) -> 'Entity':
        try:
            self.deserialize(ApiService().set(f'telegram/{self.name}', self.serialize()))
        except exceptions.UniqueConstraintViolationError:
            entities = ApiService().get(f'telegram/{self.name}', self.unique_constraint)
            
            if len(entities) > 0:
                self.id = entities[0]['id']
                
                self.save()

        return self