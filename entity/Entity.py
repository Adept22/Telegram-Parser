from abc import ABC, abstractmethod

class Entity(ABC):
    def __init__(self) -> None:
        pass

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def serialize(self) -> 'dict':
        pass

    @abstractmethod
    def deserialize(self, _dict: 'dict') -> 'Entity':
        pass

    @abstractmethod
    def save(self) -> None:
        pass