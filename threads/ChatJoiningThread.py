import random
import threading
import asyncio
import logging
from telethon import errors, functions, types

from utils.bcolors import bcolors
from processors.ApiProcessor import ApiProcessor
from core.PhonesManager import PhonesManager
from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.ClientNotAvailable import ClientNotAvailable

class ChatJoiningThread(threading.Thread):
    def __init__(self, chat):
        print(f"Creating chat {chat.id} joining phones thread...")
        logging.debug(f"Creating chat {chat.id} joining phones thread...")
        
        threading.Thread.__init__(self)
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
    
    async def wire(self, client):
        try:
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
        print(f"ChatJoiningThread: Checking {self.chat.id} for available phones.")
        logging.debug(f"ChatJoiningThread: Checking {self.chat.id} for available phones.")
        
        new_phones = dict([(p.id, p) for p in self.chat.phones])
        
        print(f"ChatJoiningThread: {len(new_phones.items())} phones initially wired with chat {self.chat.id}.")
        logging.debug(f"ChatJoiningThread: {len(new_phones.items())} phones initially wired with chat {self.chat.id}.")
        
        new_chat = None
        
        for id, phone in new_phones.items():
            try:
                client = await phone.new_client(loop=self.loop)
                
                if self.chat.internal_id != None:
                    print(f"ChatJoiningThread: Chat {self.chat.id} has internalId, try to get from Telethone by phone {id}.")
                    logging.debug(f"ChatJoiningThread: Chat {self.chat.id} has internalId, try to get from Telethone by phone {id}.")
                    
                    new_chat = await client.get_entity(types.PeerChannel(channel_id=self.chat.internal_id))
                    
                    print(f"ChatJoiningThread: Chat {self.chat.id} getted from Telethone by phone {id}.")
                    logging.debug(f"ChatJoiningThread: Chat {self.chat.id} getted from Telethone by phone {id}.")
                else:
                    raise ChatNotAvailableError()
            except (
                ClientNotAvailable, 
                ChatNotAvailableError, 
                errors.ChannelInvalidError,
                errors.ChannelPrivateError,
                errors.NeedChatInvalidError,
                errors.ChatIdInvalidError,
                errors.PeerIdInvalidError
            ) as ex:
                print(f"{bcolors.FAIL}ChatJoiningThread: Chat or channel {self.chat.id} not available for phone {id} problem. Exception: {ex}.{bcolors.ENDC}")
                logging.error(f"ChatJoiningThread: Chat or channel {self.chat.id} not available for phone {id} problem. Exception: {ex}.")
                
                del new_phones[id]
        
        if len(new_phones.items()) < 3:
            print(f"ChatJoiningThread: Chat {self.chat.id} has {len(new_phones.items())} try to wire another.")
            logging.debug(f"ChatJoiningThread: Chat {self.chat.id} has {len(new_phones.items())} try to wire another.")
            
            to_join = [PhonesManager()[k] for k in list(set(PhonesManager()) - set(new_phones))]
            to_join = list(sorted(to_join, key=lambda p: p.chats_count))
            
            print(f"ChatJoiningThread: {len(to_join)} ready for joining in chat {self.chat.id}.")
            logging.debug(f"ChatJoiningThread: {len(to_join)} ready for joining in chat {self.chat.id}.")
            
            for phone in to_join:
                try:
                    client = await phone.new_client(loop=self.loop)
                    
                    new_chat = await self.wire(client)
                except (ClientNotAvailable, ChatNotAvailableError) as ex:
                    await asyncio.sleep(random.randint(2, 5))
                    
                    continue
                else:
                    print(f"ChatJoiningThread: Phone {phone.id} succesfully wired with chat {self.chat.id}.")
                    logging.debug(f"ChatJoiningThread: Phone {phone.id} succesfully wired with chat {self.chat.id}.")
                    
                    new_phones[phone.id] = phone
                    
                    if len(new_phones.items()) >= 3:
                        print(f"ChatJoiningThread: Wired phones limit reached for chat {self.chat.id}.")
                        logging.debug(f"ChatJoiningThread: Wired phones limit reached for chat {self.chat.id}.")
                        
                        break
                    
                    await asyncio.sleep(random.randint(2, 5))
            
        if new_chat == None or len(new_phones.items()) == 0:
            print(f"{bcolors.FAIL}ChatJoiningThread: Chat {self.chat.id} not available.{bcolors.ENDC}")
            logging.error(f"ChatJoiningThread: Chat {self.chat.id} not available.")
            
            self.chat.is_available = False
            
            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
        else:
            if self.chat.internal_id != new_chat.id:
                print(f"ChatJoiningThread: Chat {self.chat.id} \'internalId\' changed, saving...")
                logging.debug(f"ChatJoiningThread: Chat {self.chat.id} \'internalId\' changed, saving...")
                
                self.chat.internalId = new_chat.id
                
                ApiProcessor().set('chat', { 
                    'id': self.chat.id, 
                    'internalId': new_chat.id,
                    'title': new_chat.title if self.chat.title == None else self.chat.title
                })
                
            if len(new_phones.items()) != len(self.chat.phones) or \
                any(x.id != y.id for x, y in zip(new_phones.values(), self.chat.phones)):
                print(f"ChatJoiningThread: Chat {self.chat.id} list of phones changed, saving...")
                logging.debug(f"ChatJoiningThread: Chat {self.chat.id} list of phones changed, saving...")
                
                self.chat.phones = new_phones.values()
                
                ApiProcessor().set('chat', { 
                    'id': self.chat.id, 
                    'phones': [{ 'id': id } for id in new_phones.keys()] 
                })
            
    def run(self):
        asyncio.run(self.async_run())
