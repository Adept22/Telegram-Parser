from __future__ import annotations
import logging
import json
from telethon import types, functions, errors

from processors.ApiProcessor import ApiProcessor
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.ChatMemberEntity import ChatMember

class ChatMemberRole(object):
    def __init__(self, member: 'ChatMember', id: 'str' = None, title: 'str' = "Участник", code: 'str' = "member"):
        self.id = id
        self.member = member
        self.title = title
        self.code = code

    async def expand(self, participant: 'types.ChannelParticipant' = None):
        if isinstance(participant, types.ChannelParticipantAdmin):
            self.title = (participant.rank if participant.rank != None else "Администратор")
            self.code = "admin"
        elif isinstance(participant, types.ChannelParticipantCreator):
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

    def save(self):
        if self.member.id == None:
            self.member.save()
            
        try:
            self.deserialize(ApiProcessor().set('telegram/chat-member-role', self.serialize()))
        except UniqueConstraintViolationError:
            members = ApiProcessor().get('telegram/chat-member-role', { 'member': { "id": self.member.id }, 'title': self.title, 'code': self.code })
            
            if len(members) > 0:
                self.id = members[0]['id']
                
                self.save()

        return self