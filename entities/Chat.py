import multiprocessing
import threading
import entities, helpers

class Chat(entities.Entity):
    def __init__(
        self,  
        id: 'str', 
        link: 'str', 
        isAvailable: 'bool', 
        internalId: 'int' = None, 
        title: 'str' = None, 
        description: 'str' = None, 
        date: 'str' = None, 
        *args, 
        **kwargs
    ):
        self.id: 'str' = id
        self.link: 'str' = link
        self.isAvailable: 'bool' = isAvailable
        self.__iternaId_condition = multiprocessing.Condition()
        self._internalId: 'int | None' = None
        self.internalId: 'int | None' = internalId
        self.title: 'str | None' = title
        self.description: 'str | None' = description
        self.date: 'str | None' = date

        self.username, self.hash = helpers.get_hash(link)

        self.phones: 'entities.TypeChatPhonesList[entities.TypeChatPhone]' = entities.ChatPhonesList()
    
    @property
    def name(self) -> 'str':
        return "chat"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return None
        
    @property
    def internalId(self) -> 'int | None':
        with self.__iternaId_condition:
            while self._internalId == None or self._internalId > 0:
                self.__iternaId_condition.wait()
                
        return self._internalId
        
    @internalId.setter
    def internalId(self, new_value: 'int | None') -> 'int | None':
        with self.__iternaId_condition:
            self._internalId = new_value
            
            if self._internalId != None:
                if self._internalId < 0:
                    self.__iternaId_condition.notify_all()

    def serialize(self) -> 'dict':
        _dict =  {
            "id": self.id,
            "link": self.link,
            "isAvailable": self.isAvailable,
            "internalId": self.internalId,
            "title": self.title,
            "description": self.description,
            "date": self.date
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'Chat':
        self.id = _dict['id']
        self.link = _dict['link']
        self.isAvailable = _dict['isAvailable']
        self.internalId = _dict.get('internalId')
        self.title = _dict.get('title')
        self.description = _dict.get('description')
        self.date = _dict.get('date')

        return self
