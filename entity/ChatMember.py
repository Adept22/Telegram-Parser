import telethon
import entity

class ChatMember(entity.Entity):
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
        
    @property
    def unique_constraint(self) -> 'dict':
        return { 'chat': { "id": self.chat.id }, "member": { "id": self.member.id } }

    async def expand(self, participant: 'telethon.types.ChannelParticipant' = None):
        if isinstance(participant, telethon.types.ChannelParticipant):
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
