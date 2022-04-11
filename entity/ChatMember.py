from telethon import types
import entity

from processors.ApiProcessor import ApiProcessor
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

class ChatMember(object):
    def __init__(self, chat: 'entity.TypeChat', member: 'entity.TypeMember', id = None, date = None, isLeft = False, roles: 'list[entity.TypeChatMemberRole]' = []):
        self.id = id
        self.chat = chat
        self.member = member
        self.date = date
        self.isLeft = isLeft
        self.roles = roles

    @property
    def name(self):
        return "chat-member"

    async def expand(self, participant: 'types.ChannelParticipant' = None):
        if isinstance(participant, types.ChannelParticipant):
            self.date = participant.date.isoformat()
        else:
            self.isLeft = True

        return self

    def serialize(self):
        _dict = {
            "id": self.id,
            "chat": self.chat.serialize(),
            "member": self.member.serialize(),
            "date": self.date,
            "isLeft": self.isLeft,
            "roles": [role.serialize() for role in self.roles],
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict'):
        self.id = _dict.get("id")
        self.chat = self.chat.deserialize(_dict.get("chat"))
        self.member = self.member.deserialize(_dict.get("member")) if self.member != None and "member" in _dict else None
        self.date = _dict.get("date")
        self.isLeft = _dict.get("isLeft")

        return self

    def save(self):
        try:
            self.deserialize(ApiProcessor().set(f'telegram/{self.name}', self.serialize()))
        except UniqueConstraintViolationError:
            members = ApiProcessor().get(f'telegram/{self.name}', { 'chat': { "id": self.chat.id }, "member": { "id": self.member.id } })
            
            if len(members) > 0:
                self.id = members[0]['id']
                
                self.save()

        return self