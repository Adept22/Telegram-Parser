import telethon
import entities

class ChatMemberRole(entities.Entity):
    def __init__(self, member: 'entities.TypeChatMember', id: 'str' = None, title: 'str' = "Участник", code: 'str' = "member", *args, **kwargs):
        self.id: 'str | None' = id
        self.member: 'entities.TypeChatMember' = member
        self.title: 'str' = title
        self.code: 'str' = code
        
    @property
    def name(self) -> 'str':
        return "chat-member-role"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return { 'member': { "id": self.member.id }, 'title': self.title, 'code': self.code }

    async def expand(self, participant: 'telethon.types.TypeChannelParticipant | telethon.types.TypeChatParticipant' = None) -> 'entities.TypeChatMemberRole':
        if isinstance(participant, (telethon.types.ChannelParticipantAdmin, telethon.types.ChatParticipantAdmin)):
            self.title = (participant.rank if participant.rank != None else "Администратор")
            self.code = "admin"
        elif isinstance(participant, (telethon.types.ChannelParticipantCreator, telethon.types.ChatParticipantCreator)):
            self.title = (participant.rank if participant.rank != None else "Создатель")
            self.code = "creator"

        return self

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "member": { "id": self.member.id } if self.member != None and self.member.id != None else None,
            "title": self.title,
            "code": self.code
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypeChatMemberRole':
        self.id = _dict["id"]
        self.member = self.member.deserialize(_dict.get("member")) if self.member != None and "member" in _dict else None
        self.title = _dict["title"]
        self.code = _dict["code"]

        return self