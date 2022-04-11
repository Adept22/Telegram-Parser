import entity
from processors.ApiProcessor import ApiProcessor
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

class MessageMedia(entity.Entity, entity.Media):
    def __init__(self, 
        internalId: 'int', 
        message: 'entity.TypeMember' = None, 
        id: 'str' = None, 
        path: 'str' = None, 
        date: 'str' = None
    ) -> None:
        self.id = id
        self.message = message
        self.internalId = internalId
        self.path = path
        self.date = date
    
    @property
    def download_path(self) -> 'str':
        return "./downloads/messages"
    
    @property
    def name(self) -> 'str':
        return "message"
    
    @property
    def entity(self) -> 'entity.TypeMessage | None':
        return self.message

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "message": self.message.serialize(),
            "internalId": self.internalId,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'MessageMedia':
        self.id = _dict.get("id")
        self.message = self.message.deserialize(_dict.get("message")) if "message" in _dict else None
        self.internalId = _dict.get("internalId")
        self.path = _dict.get("path")
        self.date = _dict.get("date")

        return self

    def save(self) -> None:
        if self.message.id == None:
            self.message.save()

        try:
            self.deserialize(ApiProcessor().set('telegram/message-media', self.serialize()))
        except UniqueConstraintViolationError:
            medias = ApiProcessor().get('telegram/message-media', { 'internalId': self.internalId })
            
            if len(medias) > 0:
                self.id = medias[0]['id']
                
                self.save()
