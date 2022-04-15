import typing, telethon
import entities

if typing.TYPE_CHECKING:
    from telethon import TelegramClient

class Member(entities.Entity):
    def __init__(self, internalId: 'int', id: 'str' = None, username: 'str' = None, firstName: 'str' = None, lastName: 'str' = None, phone: 'str' = None, about: 'str' = None, *args, **kwargs) -> None:
        self.id: 'str | None' = id
        self.internalId: 'int' = internalId
        self.username: 'str | None' = username
        self.firstName: 'str | None' = firstName
        self.lastName: 'str | None' = lastName
        self.phone: 'str | None' = phone
        self.about: 'str | None' = about

    @property
    def name(self) -> 'str':
        return "member"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return { 'internalId': self.internalId }

    async def expand(self, client: 'TelegramClient') -> 'Member':
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
            "username": self.username,
            "firstName": self.firstName,
            "lastName": self.lastName,
            "phone": self.phone,
            "about": self.about
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypeMember':
        self.id = _dict.get("id")
        self.internalId = _dict.get("internalId")
        self.username = _dict.get("username")
        self.firstName = _dict.get("firstName")
        self.lastName = _dict.get("lastName")
        self.phone = _dict.get("phone")
        self.about = _dict.get("about")

        return self
