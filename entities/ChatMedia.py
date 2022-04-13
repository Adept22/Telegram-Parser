import entities

class ChatMedia(entities.Entity, entities.Media):
    def __init__(self, internalId: 'int', chat: 'entities.TypeChat' = None, id = None, path = None, date = None):
        self.id: 'str | None' = id
        self.chat: 'entities.TypeChat' = chat
        self.internalId: 'int' = internalId
        self.path: 'str | None' = path
        self.date: 'str | None' = date
        
    @property
    def name(self) -> 'str':
        return "chat"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return { "internalId": self.internalId }

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": self.chat.serialize(),
            "internalId": self.internalId,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypeChatMedia':
        self.id = _dict.get("id")
        self.chat = self.chat.deserialize(_dict.get("chat"))
        self.internalId = _dict.get("internalId")
        self.path = _dict.get("path")
        self.date = _dict.get("date")

        return self
