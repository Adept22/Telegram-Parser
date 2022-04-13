import telethon
import entities, exceptions
from services import PhonesManager
from processes import ChatMediaProcess, MembersProcess, MessagesProcess
from utils import get_hash

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from telethon import TelegramClient, types

class Chat(entities.Entity):
    def __init__(self,  id: 'str', link: 'str', isAvailable: 'bool', availablePhones: 'list[entities.TypePhone]' = [], phones: 'list[entities.TypePhone]' = [], internalId: 'int' = None, title: 'str' = None, description: 'str' = None, date: 'str' = None, *args, **kwargs):
        self.id: 'str' = id
        self.link: 'str' = link
        self.isAvailable: 'bool' = isAvailable
        self.availablePhones: 'list[entities.TypePhone]' = availablePhones
        self.phones: 'list[entities.TypePhone]' = phones
        self.internalId: 'int | None' = internalId
        self.title: 'str | None' = title
        self.description: 'str | None' = description
        self.date: 'str | None' = date

        self.username, self.hash = get_hash(link)

        self.chat_media_process = ChatMediaProcess(self)
        self.members_process = MembersProcess(self)
        self.messages_process = MessagesProcess(self)
        
    @property
    def name(self) -> 'str':
        return "chat"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    def serialize(self) -> 'dict':
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

    def deserialize(self, _dict: 'dict') -> 'entities.TypeChat':
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

    def add_phone(self, phone: 'entities.TypePhone'):
        if not phone.id in [_p.id for _p in self.phones]:
            self.phones.append(phone)

    def remove_phone(self, phone: 'entities.TypePhone'):
        self.phones = [_p for _p in self.phones if _p.id != phone.id]

    def add_available_phone(self, phone: 'entities.TypePhone'):
        if not phone.id in [_p.id for _p in self.availablePhones]:
            self.availablePhones.append(phone)

    def remove_available_phone(self, phone):
        self.availablePhones = [_p for _p in self.availablePhones if _p.id != phone.id]
            
    async def get_tg_entity(self, client: 'TelegramClient') -> 'telethon.types.TypeChat':
        try:
            if self.internalId != None:
                try:
                    return await client.get_entity(telethon.types.PeerChannel(channel_id=self.internalId))
                except ValueError:
                    try:
                        return await client.get_entity(telethon.types.PeerChat(channel_id=self.internalId))
                    except:
                        pass

            if self.hash != None:
                chat_invite = await client(telethon.functions.messages.CheckChatInviteRequest(hash=self.hash))
                
                if isinstance(chat_invite, (telethon.types.ChatInviteAlready, telethon.types.ChatInvitePeek)):
                    return chat_invite.chat
            elif self.username != None:
                return await client.get_entity(self.username)
            
            raise exceptions.ChatNotAvailableError("Unrecognized chat")
        except (
            ValueError,
            ### ------------------------
            telethon.errors.ChannelInvalidError, 
            telethon.errors.ChannelPrivateError, 
            telethon.errors.ChannelPublicGroupNaError, 
            ### ------------------------
            telethon.errors.NeedChatInvalidError, 
            telethon.errors.ChatIdInvalidError, 
            telethon.errors.PeerIdInvalidError, 
            ### ------------------------
            telethon.errors.InviteHashEmptyError, 
            telethon.errors.InviteHashExpiredError, 
            telethon.errors.InviteHashInvalidError
        ) as ex:
            raise exceptions.ChatNotAvailableError(ex)

    async def join_channel(self, client: 'TelegramClient') -> 'telethon.types.TypeChat':
        try:
            updates = await client(
                telethon.functions.channels.JoinChannelRequest(channel=self.username) 
                    if self.hash is None else 
                        telethon.functions.messages.ImportChatInviteRequest(hash=self.hash)
            )
        except (
            ValueError,
            ### -----------------------------
            telethon.errors.UsernameNotOccupiedError,
            ### -----------------------------
            telethon.errors.ChannelPrivateError, 
            telethon.errors.InviteHashExpiredError, 
            telethon.errors.UsersTooMuchError,
            ### -----------------------------
            telethon.errors.ChannelInvalidError, 
            telethon.errors.InviteHashEmptyError, 
            telethon.errors.InviteHashInvalidError
        ) as ex:
            raise exceptions.ChatNotAvailableError(ex)
        except telethon.errors.UserAlreadyParticipantError as ex:
            return await self.get_tg_entity(client)
        else:
            return updates.chats[0]
