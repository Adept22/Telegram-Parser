from __future__ import annotations
from telethon import functions

from processors.ApiProcessor import ApiProcessor
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.ChatEntity import Chat
    from models.ChatMemberEntity import ChatMember

class Message(object):
    def __init__(self, 
        internalId: 'int' = None,
        chat: 'Chat' = None,
        id = None,
        text = None,
        member: 'ChatMember' = None,
        replyTo: 'Message' = None,
        isPinned = None,
        forwardedFromId = None,
        forwardedFromName = None,
        groupedId = None,
        date = None
    ):
        self.id = id
        self.internalId = internalId
        self.text = text
        self.chat = chat
        self.member = member
        self.replyTo = replyTo
        self.isPinned = isPinned
        self.forwardedFromId = forwardedFromId
        self.forwardedFromName = forwardedFromName
        self.groupedId = groupedId
        self.date = date

    async def expand(self, client):
        full_user = await client(functions.users.GetFullUserRequest(id=self.internalId))

        self.username = full_user.user.username
        self.firstName = full_user.user.first_name
        self.lastName = full_user.user.last_name
        self.phone = full_user.user.phone
        self.about = full_user.about

        return self

    def serialize(self):
        _dict = {
            "id": self.id, 
            "internalId": self.internalId, 
            "text": self.text, 
            "chat": self.chat.serialize(), 
            "member": self.member.serialize() if self.member != None else None, 
            "replyTo": self.replyTo.serialize() if self.replyTo != None else None, 
            "isPinned": self.isPinned, 
            "forwardedFromId": self.forwardedFromId, 
            "forwardedFromName": self.forwardedFromName, 
            "groupedId": self.groupedId, 
            "date": self.date
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict'):
        self.id = _dict.get("id")
        self.internalId = _dict.get("internalId")
        self.text = _dict.get("text")
        self.chat = self.chat.deserialize(_dict.get("chat"))
        self.member = self.member.deserialize(_dict.get("member")) if self.member != None and "member" in _dict else None
        self.replyTo = self.replyTo.deserialize(_dict.get("replyTo")) if self.replyTo != None and "replyTo" in _dict else None
        self.isPinned = _dict.get("isPinned")
        self.forwardedFromId = _dict.get("forwardedFromId")
        self.forwardedFromName = _dict.get("forwardedFromName")
        self.groupedId = _dict.get("groupedId")
        self.date = _dict.get("date")

        return self

    def save(self):
        try:
            self.deserialize(ApiProcessor().set('telegram/message', self.serialize()))
        except UniqueConstraintViolationError:
            messages = ApiProcessor().get('telegram/message', { 'internalId': self.internalId, 'chat': { "id": self.chat.id } })
            
            if len(messages) > 0:
                self.id = messages[0]['id']
                
                self.save()

        return self