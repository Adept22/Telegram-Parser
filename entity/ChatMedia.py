import entity

class ChatMedia(entity.Entity, entity.Media):
    def __init__(self, internalId: 'int', chat: 'entity.TypeChat' = None, id = None, path = None, date = None):
        self.id = id
        self.chat = chat
        self.internalId = internalId
        self.path = path
        self.date = date
        
    @property
    def name(self):
        return "chat"
        
    @property
    def unique_constraint(self) -> 'dict':
        return { "internalId": self.internalId }

    def serialize(self):
        _dict = {
            "id": self.id,
            "chat": self.chat.serialize(),
            "internalId": self.internalId,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict'):
        self.id = _dict.get("id")
        self.chat = self.chat.deserialize(_dict.get("chat"))
        self.internalId = _dict.get("internalId")
        self.path = _dict.get("path")
        self.date = _dict.get("date")

        return self
