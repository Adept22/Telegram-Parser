import telethon
import entity

class ChatMemberRole(entity.Entity):
    def __init__(self, member: 'entity.TypeChatMember', id: 'str' = None, title: 'str' = "Участник", code: 'str' = "member"):
        self.id = id
        self.member = member
        self.title = title
        self.code = code
        
    @property
    def name(self):
        return "chat-member-role"
        
    @property
    def unique_constraint(self) -> 'dict':
        return { 'member': { "id": self.member.id }, 'title': self.title, 'code': self.code }

    async def expand(self, participant: 'telethon.types.ChannelParticipant' = None):
        if isinstance(participant, telethon.types.ChannelParticipantAdmin):
            self.title = (participant.rank if participant.rank != None else "Администратор")
            self.code = "admin"
        elif isinstance(participant, telethon.types.ChannelParticipantCreator):
            self.title = (participant.rank if participant.rank != None else "Создатель")
            self.code = "creator"

        return self

    def serialize(self):
        _dict = {
            "id": self.id,
            "member": self.member.serialize(),
            "title": self.title,
            "code": self.code
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict'):
        self.id = _dict.get("id")
        self.member = self.member.deserialize(_dict.get("member")) if self.member != None and "member" in _dict else None
        self.title = _dict.get("title")
        self.code = _dict.get("code")

        return self