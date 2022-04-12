import telethon
import entity

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from telethon import TelegramClient

class Member(entity.Entity):
    def __init__(self, internalId: 'int', id: 'str' = None, username: 'str' = None, firstName: 'str' = None, lastName: 'str' = None, phone: 'str' = None, about: 'str' = None) -> None:
        self.id = id
        self.internalId = internalId
        self.username = username
        self.firstName = firstName
        self.lastName = lastName
        self.phone = phone
        self.about = about

    @property
    def name(self):
        return "member"
        
    @property
    def unique_constraint(self) -> 'dict':
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

    def deserialize(self, _dict: 'dict') -> 'Member':
        self.id = _dict.get("id")
        self.internalId = _dict.get("internalId")
        self.username = _dict.get("username")
        self.firstName = _dict.get("firstName")
        self.lastName = _dict.get("lastName")
        self.phone = _dict.get("phone")
        self.about = _dict.get("about")

        return self
