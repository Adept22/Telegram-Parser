import telethon
import entities

class Message(entities.Entity):
    def __init__(self, internalId: 'int', chat: 'entities.TypeChat', id: 'str' = None, text: 'str' = None, member: 'entities.TypeChatMember' = None, replyTo: 'entities.TypeMessage' = None, isPinned: 'bool' = False, forwardedFromId: 'int' = None, forwardedFromName: 'str' = None, groupedId: 'int' = None, date: 'str' = None, *args, **kwargs):
        self.id: 'str | None' = id
        self.internalId: 'int' = internalId
        self.text: 'str | None' = text
        self.chat: 'entities.TypeChat' = chat
        self.member: 'entities.TypeMember | None' = member
        self.replyTo: 'entities.TypeMessage | None' = replyTo
        self.isPinned: 'bool' = isPinned
        self.forwardedFromId: 'int | None' = forwardedFromId
        self.forwardedFromName: 'str | None' = forwardedFromName
        self.groupedId: 'int | None' = groupedId
        self.date: 'str | None' = date

    @property
    def name(self) -> 'str':
        return "message"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return { 'internalId': self.internalId, 'chat': { "id": self.chat.id } }

    async def expand(self, client) -> 'entities.TypeMessage':
        full_user = await client(telethon.functions.users.GetFullUserRequest(id=self.internalId))

        self.username = full_user.user.username
        self.firstName = full_user.user.first_name
        self.lastName = full_user.user.last_name
        self.phone = full_user.user.phone
        self.about = full_user.about

        return self

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id, 
            "internalId": self.internalId, 
            "text": self.text, 
            "chat": { "id": self.chat.id },
            "member": { "id": self.member.id } if self.member != None and self.member.id != None else None, 
            "replyTo": { "id": self.replyTo.id } if self.replyTo != None and self.replyTo.id != None else None, 
            "isPinned": self.isPinned, 
            "forwardedFromId": self.forwardedFromId, 
            "forwardedFromName": self.forwardedFromName, 
            "groupedId": self.groupedId, 
            "date": self.date
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypeMessage':
        self.id = _dict.get("id")
        self.internalId = _dict.get("internalId")
        self.text = _dict.get("text")
        # self.chat = self.chat.deserialize(_dict.get("chat"))
        self.member = self.member.deserialize(_dict.get("member")) if self.member != None and "member" in _dict else None
        self.replyTo = self.replyTo.deserialize(_dict.get("replyTo")) if self.replyTo != None and "replyTo" in _dict else None
        self.isPinned = _dict.get("isPinned")
        self.forwardedFromId = _dict.get("forwardedFromId")
        self.forwardedFromName = _dict.get("forwardedFromName")
        self.groupedId = _dict.get("groupedId")
        self.date = _dict.get("date")

        return self
