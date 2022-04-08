from __future__ import annotations
import json
from telethon import functions

from processors.ApiProcessor import ApiProcessor
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

class Member(object):
    def __init__(self, internalId: 'int', id=None, username=None, firstName=None, lastName=None, phone=None, about=None):
        self.id = id
        self.internalId = internalId
        self.username = username
        self.firstName = firstName
        self.lastName = lastName
        self.phone = phone
        self.about = about

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
            "username": self.username,
            "firstName": self.firstName,
            "lastName": self.lastName,
            "phone": self.phone,
            "about": self.about
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict = {}):
        self.id = _dict.get("id")
        self.internalId = _dict.get("internalId")
        self.username = _dict.get("username")
        self.firstName = _dict.get("firstName")
        self.lastName = _dict.get("lastName")
        self.phone = _dict.get("phone")
        self.about = _dict.get("about")

        return self

    def save(self):
        try:
            self.deserialize(ApiProcessor().set('telegram/member', self.serialize()))
        except UniqueConstraintViolationError:
            members = ApiProcessor().get('telegram/member', { 'internalId': self.internalId })
            
            if len(members) > 0:
                self.id = members[0]['id']
                
                self.save()

        return self