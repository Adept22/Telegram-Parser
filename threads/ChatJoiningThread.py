import threading
import asyncio
import random
import logging

from telethon import functions, errors, types

from processors.ApiProcessor import ApiProcessor
from core.PhonesManager import PhonesManager
from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.ClientNotAvailableError import ClientNotAvailableError

class ChatJoiningThread(threading.Thread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'ChatJoiningThread-{chat.id}')
        
        self.chat = chat
        
        self.exit_event = threading.Event()
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def wire(self, phone):
        try:
            client = await phone.new_client(loop=self.loop)
            
            updates = await client(
                functions.channels.JoinChannelRequest(channel=self.chat.username) 
                    if self.chat.hash is None else 
                        functions.messages.ImportChatInviteRequest(hash=self.chat.hash)
            )
            
            return updates.chats[0]
        except (
            errors.ChannelsTooMuchError, 
            errors.ChannelPrivateError, 
            errors.InviteHashExpiredError, 
            errors.UsersTooMuchError,
            ### -----------------------------
            errors.ChannelInvalidError, 
            errors.InviteHashEmptyError, 
            errors.InviteHashInvalidError, 
            errors.SessionPasswordNeededError
        ) as ex:
            raise ChatNotAvailableError(ex)
        except errors.UserAlreadyParticipantError as ex:
            try:
                client = await phone.new_client(loop=self.loop)
                
                if self.chat.internal_id != None:
                    return await client.get_entity(types.PeerChannel(channel_id=self.chat.internal_id))
                else:
                    chat_invite = await client(functions.messages.CheckChatInviteRequest(hash=self.chat.hash))
                    
                    if isinstance(chat_invite, (types.ChatInviteAlready, types.ChatInvitePeek)):
                        return chat_invite.chat
                    else:
                        raise ValueError()
            except (
                errors.ChannelInvalidError,
                errors.ChannelPrivateError,
                ### ------------------------
                errors.InviteHashEmptyError,
                errors.InviteHashExpiredError,
                errors.InviteHashInvalidError
            ) as ex:
                raise ChatNotAvailableError(ex)
            
    async def async_run(self):
        new_chat = None
        new_phones = dict([(p.id, p) for p in self.chat.phones])
        
        logging.debug(f"Chat {self.chat.id} has {len(new_phones.items())} wired phones.")
        
        to_join = [PhonesManager()[k] for k in list(set(PhonesManager()) - set(new_phones))]
        to_join = list(sorted(to_join, key=lambda p: p.chats_count))
        
        logging.debug(f"{len(to_join)} ready for joining in chat {self.chat.id}.")
        
        for phone in to_join:
            try:
                new_chat = await self.wire(phone)
            except (ClientNotAvailableError, ChatNotAvailableError) as ex:
                logging.error(f"Chat {self.chat.id} not available for phone {phone.id}. Exception: {ex}.")
                
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            except errors.FloodWaitError as ex:
                logging.error(f"Chat {self.chat.id} wiring for phone {phone.id} must wait. Exception: {ex}.")
                
                await asyncio.sleep(ex.seconds)
            else:
                logging.info(f"Phone {phone.id} succesfully wired with chat {self.chat.id}.")
                
                new_phones[phone.id] = phone
                
                if len(new_phones.items()) >= 3:
                    logging.debug(f"Wired phones limit reached for chat {self.chat.id}.")
                    
                    break
                
                await asyncio.sleep(random.randint(2, 5))
            
        if new_chat == None or len(new_phones.items()) == 0:
            logging.error(f"Chat {self.chat.id} not available.")
            
            self.chat.is_available = False
            
            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
        else:
            if self.chat.internal_id != new_chat.id:
                logging.info(f"Chat {self.chat.id} \'internalId\' changed, saving...")
                
                ApiProcessor().set('chat', { 
                    'id': self.chat.id, 
                    'internalId': new_chat.id,
                    'title': new_chat.title if self.chat.title == None else self.chat.title
                })
                
            if len(new_phones.items()) != len(self.chat.phones) or \
                any(x.id != y.id for x, y in zip(new_phones.values(), self.chat.phones)):
                logging.info(f"Chat {self.chat.id} list of phones changed, saving...")
                
                ApiProcessor().set('chat', { 
                    'id': self.chat.id, 
                    'phones': [{ 'id': id } for id in new_phones.keys()] 
                })
                
        self.chat.chat_joining_thread = None

    def run(self):
        asyncio.run(self.async_run())
