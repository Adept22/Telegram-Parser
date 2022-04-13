import telethon
import entities

class ChatMember(entities.Entity):
    def __init__(self, chat: 'entities.TypeChat', member: 'entities.TypeMember', id: 'str' = None, date: 'str' = None, isLeft: 'bool' = False, roles: 'list[entities.TypeChatMemberRole]' = [], *args, **kwargs):
        self.id: 'str | None' = id
        self.chat: 'entities.TypeChat' = chat
        self.member: 'entities.TypeMember' = member
        self.date: 'str | None' = date
        self.isLeft: 'bool' = isLeft
        self.roles: 'list[entities.TypeChatMemberRole]' = roles

    @property
    def name(self) -> 'str':
        return "chat-member"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return { 'chat': { "id": self.chat.id }, "member": { "id": self.member.id } }

    async def expand(self, participant: 'telethon.types.TypeChannelParticipant | telethon.types.TypeChatParticipant' = None) -> 'entities.TypeChatMember':
        if isinstance(participant, (telethon.types.ChannelParticipant, telethon.types.ChatParticipant)):
            self.date = participant.date.isoformat()
        else:
            self.isLeft = True

        return self

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "chat": self.chat.serialize(),
            "member": self.member.serialize(),
            "date": self.date,
            "isLeft": self.isLeft,
            "roles": [role.serialize() for role in self.roles],
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypeChatMember':
        self.id = _dict.get("id")
        self.chat = self.chat.deserialize(_dict.get("chat"))
        self.member = self.member.deserialize(_dict.get("member")) if self.member != None and "member" in _dict else None
        self.date = _dict.get("date")
        self.isLeft = _dict.get("isLeft")

        return self
