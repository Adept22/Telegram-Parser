import entities

class MessageMedia(entities.Entity, entities.Media):
    def __init__(self, internalId: 'int', message: 'entities.TypeMessage' = None, id: 'str' = None, path: 'str' = None, date: 'str' = None, *args, **kwargs) -> None:
        self.id: 'str | None' = id
        self.message: 'entities.TypeMessage' = message
        self.internalId: 'int' = internalId
        self.path: 'str | None' = path
        self.date: 'str | None' = date
    
    @property
    def download_path(self) -> 'str':
        return "./downloads/messages"
    
    @property
    def name(self) -> 'str':
        return "message-media"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return { 'internalId': self.internalId }

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "message": { "id": self.message.id } if self.message != None and self.message.id != None else None,
            "internalId": self.internalId,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypeMessageMedia':
        self.id = _dict.get("id")
        self.message = self.message.deserialize(_dict.get("message")) if "message" in _dict else None
        self.internalId = _dict.get("internalId")
        self.path = _dict.get("path")
        self.date = _dict.get("date")

        return self
