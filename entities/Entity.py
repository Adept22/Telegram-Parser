from abc import ABC, abstractmethod
import entities

import exceptions
from services import ApiService

class Entity(ABC):
    @property
    @abstractmethod
    def name(self) -> 'str':
        raise NotImplementedError

    @property
    @abstractmethod
    def unique_constraint(self) -> 'dict | None':
        raise NotImplementedError

    @abstractmethod
    def serialize(self) -> 'dict':
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, _dict: 'dict') -> 'entities.TypeEntity':
        raise NotImplementedError

    def save(self) -> 'entities.TypeEntity':
        try:
            self.deserialize(ApiService().set(f'telegram/{self.name}', self.serialize()))
        except exceptions.UniqueConstraintViolationError as ex:
            if self.unique_constraint is None:
                raise ex
                
            entities = ApiService().get(f'telegram/{self.name}', self.unique_constraint)
            
            if len(entities) > 0:
                self.id = entities[0]['id']
                
                self.save()

        return self