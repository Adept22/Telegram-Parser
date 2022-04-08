from __future__ import annotations

from models.MediaEntity import Media
from processors.ApiProcessor import ApiProcessor
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.ChatEntity import Chat

class ChatMedia(Media):
    def __init__(self, internalId: 'int', chat: 'Chat' = None, id = None, path = None, date = None):
        self.id = id
        self.chat = chat
        self.internalId = internalId
        self.path = path
        self.date = date
    
    @property
    def download_path(self):
        return "./downloads/chats"
    
    @property
    def name(self):
        return "chat"
    
    @property
    def entity(self):
        return self.chat

    def serialize(self):
        _dict = {
            "id": self.id,
            "chat": self.chat.serialize(),
            "internalId": self.internalId,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict = {}):
        self.id = _dict.get("id")
        self.chat = self.chat.deserialize(_dict.get("chat"))
        self.internalId = _dict.get("internalId")
        self.path = _dict.get("path")
        self.date = _dict.get("date")

        return self

    def save(self):
        try:
            self.deserialize(ApiProcessor().set('telegram/chat-media', self.serialize()))
        except UniqueConstraintViolationError:
            medias = ApiProcessor().get('telegram/chat-media', { 'internalId': self.internalId })
            
            if len(medias) > 0:
                self.id = medias[0]['id']
                
                self.save()

        return self
