from __future__ import annotations

from models.MediaEntity import Media
from processors.ApiProcessor import ApiProcessor
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.MemberEntity import Member

class MessageMedia(Media):
    def __init__(self, internalId: 'int', message: 'Member' = None, id = None, path = None, date = None):
        self.id = id
        self.message = message
        self.internalId = internalId
        self.path = path
        self.date = date
    
    @property
    def download_path(self):
        return "./downloads/messages"
    
    @property
    def name(self):
        return "message"
    
    @property
    def entity(self):
        return self.message

    def serialize(self):
        _dict = {
            "id": self.id,
            "message": self.message.serialize(),
            "internalId": self.internalId,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict = {}):
        self.id = _dict.get("id")
        self.message = self.message.deserialize(_dict.get("message"))
        self.internalId = _dict.get("internalId")
        self.path = _dict.get("path")
        self.date = _dict.get("date")

        return self

    def save(self):
        if self.message.id == None:
            self.message.save()

        try:
            self.deserialize(ApiProcessor().set('telegram/message-media', self.serialize()))
        except UniqueConstraintViolationError:
            medias = ApiProcessor().get('telegram/message-media', { 'internalId': self.internalId })
            
            if len(medias) > 0:
                self.id = medias[0]['id']
                
                self.save()

        return self
