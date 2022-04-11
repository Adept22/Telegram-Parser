from __future__ import annotations

import logging
import json

from telethon import types, functions, errors

from processors.ApiProcessor import ApiProcessor
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.ChatEntity import Chat
    from models.MemberEntity import Member
    from models.ChatMemberRoleEntity import ChatMemberRole

class ChatMember(object):
    def __init__(self, chat: 'Chat', member: 'Member', id = None, date = None, isLeft = False, roles: 'list[ChatMemberRole]' = []):
        self.id = id
        self.chat = chat
        self.member = member
        self.date = date
        self.isLeft = isLeft
        self.roles = roles

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

    def deserialize(self, _dict = {}):
        self.id = _dict.get("id")
        self.chat = self.chat.deserialize(_dict.get("chat"))
        self.member = self.member.deserialize(_dict.get("member"))
        self.date = _dict.get("date")
        self.isLeft = _dict.get("isLeft")

        return self

    def save(self):
        if self.member.id == None:
            self.member.save()

        try:
            self.deserialize(ApiProcessor().set('telegram/chat-member', self.serialize()))
        except UniqueConstraintViolationError:
            members = ApiProcessor().get('telegram/chat-member', { 'chat': { "id": self.chat.id }, "member": { "id": self.member.id } })
            
            if len(members) > 0:
                self.id = members[0]['id']
                
                self.save()

        return self