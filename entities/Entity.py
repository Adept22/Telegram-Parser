from abc import ABC, abstractmethod
import entities

import exceptions
from services import ApiService

class Entity(ABC):
    @property
    @abstractmethod
    def name(self) -> 'str':
        """
        Название сущности в пути API.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def unique_constraint(self) -> 'dict | None':
        """
        Свойства для проверки существования сущности, они же отражают уникольность.
        """
        raise NotImplementedError

    @abstractmethod
    def serialize(self) -> 'dict':
        """
        Сериализация сущности. Т.е. из `self` в `dict`
        """
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, _dict: 'dict') -> 'entities.TypeEntity':
        """
        Десериализация сущности. Т.е. из `dict` в `self`
        """
        raise NotImplementedError

    def update(self) -> 'entities.TypeEntity':
        """
        Обновляет текущую сущность из API.
        """
        if not self.id:
            raise ValueError("Entity hasn't id")

        self.deserialize(ApiService().get(f'telegram/{self.name}', { "id": self.id }))

    def save(self) -> 'entities.TypeEntity':
        """
        Создает/изменяет сущность в API.
        """
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

    def delete(self) -> 'None':
        """
        Удаляет сущность из API.
        """
        ApiService().delete(f'telegram/{self.name}', self.serialize())