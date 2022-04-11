from telethon import types, functions, errors
from utils import get_hash
import entity

from core.PhonesManager import PhonesManager
from processors.ApiProcessor import ApiProcessor
from processes.ChatMediaProcess import ChatMediaProcess
from processes.MembersProcess import MembersProcess
from processes.MessagesProcess import MessagesProcess
from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

class Chat(entity.Entity):
    def __init__( self,  id: 'str', link: 'str', isAvailable: 'bool', availablePhones: 'list[entity.TypePhone]', phones: 'list[entity.TypePhone]', internalId: 'int' = None, title: 'str' = None, description: 'str' = None, date: 'str' = None, ):
        self.id = id
        self.link = link
        self.isAvailable = isAvailable
        self.availablePhones = availablePhones
        self.phones = phones
        self.internalId = internalId
        self.title = title
        self.description = description
        self.date = date

        self.username, self.hash = get_hash(link)

        self.chat_media_process = None
        self.members_process = None
        self.messages_process = None
        
    @property
    def name(self):
        return "chat"

    def serialize(self):
        _dict =  {
            "id": self.id,
            "link": self.link,
            "isAvailable": self.isAvailable,
            "internalId": self.internalId,
            "title": self.title,
            "description": self.description,
            "date": self.date,
            "availablePhones": [p.serialize() for p in self.availablePhones],
            "phones": [p.serialize() for p in self.phones],
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'Chat':
        self.id = _dict.get('id')
        self.link = _dict.get('link')
        self.isAvailable = _dict.get('isAvailable')
        self.availablePhones = [PhonesManager()[p['id']] for p in _dict.get('availablePhones', []) if p['id'] in PhonesManager()]
        self.phones = [PhonesManager()[p['id']] for p in _dict.get('phones', []) if p['id'] in PhonesManager()]
        self.internalId = _dict.get('internalId')
        self.title = _dict.get('title')
        self.description = _dict.get('description')
        self.date = _dict.get('date')

        return self

    def save(self):
        try:
            self.deserialize(ApiProcessor().set(f'telegram/{self.name}', self.serialize()))
        except UniqueConstraintViolationError:
            members = ApiProcessor().get(f'telegram/{self.name}', { "internalId": self.internalId })
            
            if len(members) > 0:
                self.id = members[0]['id']
                
                self.save()

        return self
            
    async def get_internal_id(self, client):
        try:
            if self.internal_id != None:
                try:
                    return await client.get_entity(types.PeerChannel(channel_id=self.internal_id))
                except:
                    pass

            if self.hash != None:
                chat_invite = await client(functions.messages.CheckChatInviteRequest(hash=self.hash))
                
                if isinstance(chat_invite, (types.ChatInviteAlready, types.ChatInvitePeek)):
                    return chat_invite.chat
            elif self.username != None:
                return await client.get_entity(self.username)
            
            raise ChatNotAvailableError("Unrecognized chat")
        except (
            ValueError,
            ### ------------------------
            errors.ChannelInvalidError, 
            errors.ChannelPrivateError, 
            errors.ChannelPublicGroupNaError, 
            ### ------------------------
            errors.NeedChatInvalidError, 
            errors.ChatIdInvalidError, 
            errors.PeerIdInvalidError, 
            ### ------------------------
            errors.InviteHashEmptyError, 
            errors.InviteHashExpiredError, 
            errors.InviteHashInvalidError
        ) as ex:
            raise ChatNotAvailableError(ex)

    async def join_channel(self, client):
        try:
            updates = await client(
                functions.channels.JoinChannelRequest(channel=self.username) 
                    if self.hash is None else 
                        functions.messages.ImportChatInviteRequest(hash=self.hash)
            )
        except (
            ValueError,
            ### -----------------------------
            errors.UsernameNotOccupiedError,
            ### -----------------------------
            errors.ChannelPrivateError, 
            errors.InviteHashExpiredError, 
            errors.UsersTooMuchError,
            ### -----------------------------
            errors.ChannelInvalidError, 
            errors.InviteHashEmptyError, 
            errors.InviteHashInvalidError
        ) as ex:
            raise ChatNotAvailableError(ex)
        except errors.UserAlreadyParticipantError as ex:
            return await self.get_internal_id(client)
        else:
            return updates.chats[0]
