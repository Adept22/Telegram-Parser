import logging
import re
import threading
from utils import get_hash
from telethon import types, functions, errors

from processors.ApiProcessor import ApiProcessor
from core.PhonesManager import PhonesManager
from threads.ChatThread import ChatThread
from threads.ChatMediaThread import ChatMediaThread
from threads.MembersThread import MembersThread
from threads.MessagesThread import MessagesThread
from threads.ChatMediaThread import ChatMediaThread
from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.ClientNotAvailableError import ClientNotAvailableError

class Chat(object):
    def __init__(self, _dict):
        if not 'id' in _dict or _dict['id'] is None:
            raise Exception('Unexpected chat id')

        if not 'link' in _dict or _dict['link'] is None:
            raise Exception('Unexpected chat link')

        self.username, self.hash = get_hash(_dict['link'])
        
        self._title = None
        self.link = None
        self._internal_id = None
        self.is_available = False

        self._available_phones = []
        self._phones = []

        self.chat_thread = None
        self.chat_media_thread = None
        self.members_thread = None
        self.messages_thread = None

        self.phones_lock = threading.Lock()
        self.init_event = threading.Event()
        
        self.from_dict(_dict)

    def __del__(self):
        if self.init_event.is_set():
            self.init_event.clear()
        # TODO: Мы должны убивать треды при удалении чата.
        pass
        
    @property
    def phones(self):
        return self._phones
    
    @phones.setter
    def phones(self, new_value):
        new_phones = [PhonesManager()[p['id']] for p in new_value if p['id'] in PhonesManager()]
        
        if len(new_phones) != len(self._phones) or \
            any(x.id != y.id for x, y in zip(new_phones, self._phones)):
            logging.info(f"Chat {self.id} list of available phones changed. Now it\'s {len(new_phones)}.")
            
            ApiProcessor().set('chat', { 
                'id': self.id, 
                'phones': [{ 'id': phone.id } for phone in new_phones] 
            })
        
        self._phones = new_phones
        
    @property
    def available_phones(self):
        return self._available_phones
    
    @available_phones.setter
    def available_phones(self, new_value):
        new_available_phones = [PhonesManager()[p['id']] for p in new_value if p['id'] in PhonesManager()]
        
        if len(new_available_phones) != len(self._available_phones) or \
            any(x.id != y.id for x, y in zip(new_available_phones, self._available_phones)):
            logging.info(f"Chat {self.id} list of available phones changed. Now it\'s {len(new_available_phones)}.")
            
            ApiProcessor().set('chat', { 
                'id': self.id, 
                'availablePhones': [{ 'id': phone.id } for phone in new_available_phones] 
            })
            
        self._available_phones = new_available_phones
        
    @property
    def internal_id(self):
        return self._internal_id
    
    @internal_id.setter
    def internal_id(self, new_value):
        if self._internal_id != new_value:
            logging.info(f"Chat {self.id} internal id changed.")
            
            ApiProcessor().set('chat', { 
                'id': self.id, 
                'internalId': new_value
            })

        self._internal_id = new_value
        
    @property
    def title(self):
        return self._title
    
    @title.setter
    def title(self, new_value):
        if self._title != new_value:
            logging.info(f"Chat {self.id} title changed.")
            
            ApiProcessor().set('chat', { 
                'id': self.id, 
                'title': new_value
            })

        self._title = new_value
        
    def from_dict(self, _dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in _dict:
            setattr(self, pattern.sub('_', key).lower(), _dict[key])
            
        return self

    def run(self):
        self.chat_thread = ChatThread(self)
        self.chat_thread.start()

        self.chat_media_thread = ChatMediaThread(self)
        self.chat_media_thread.start()

        self.members_thread = MembersThread(self)
        self.members_thread.start()

        self.messages_thread = MessagesThread(self)
        self.messages_thread.start()

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
            return
        else:
            return updates.chats[0]
