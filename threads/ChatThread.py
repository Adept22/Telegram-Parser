from distutils.log import error
import threading
import asyncio
import random
import logging

from telethon import functions, errors, types

from processors.ApiProcessor import ApiProcessor
from core.PhonesManager import PhonesManager
from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.ClientNotAvailableError import ClientNotAvailableError

class ChatThread(threading.Thread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'ChatThread-{chat.id}')
        
        self.chat = chat
        
        self.exit_event = threading.Event()
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def check_phones(self, phones):
        new_phones = phones
        
        for phone in phones.values():
            try:
                client = await phone.new_client(loop=self.loop)
                
                await client.get_entity(types.PeerChannel(channel_id=self.chat.internal_id))
                
                logging.info(f"Chat {self.chat.id} available for phone {phone.id}.")
            except (
                errors.ChannelInvalidError, 
                errors.ChannelPrivateError, 
                errors.NeedChatInvalidError, 
                errors.ChatIdInvalidError, 
                errors.PeerIdInvalidError, 
                ### ------------------------
                ClientNotAvailableError, 
                ChatNotAvailableError
            ) as ex:
                logging.error(f"Chat {self.chat.id} not available for phone {phone.id}. Exception: {ex}.")
                
                del new_phones[phone.id]
            else:
                await asyncio.sleep(random.randint(2, 5))
        
        return new_phones
            
    async def get_tg_chat(self, phones):
        for phone in phones.values():
            client = await phone.new_client(loop=self.loop)
            
            try:
                if self.chat.internal_id != None:
                    return await client.get_entity(types.PeerChannel(channel_id=self.chat.internal_id))
                elif self.chat.hash != None:
                    chat_invite = await client(functions.messages.CheckChatInviteRequest(hash=self.chat.hash))
                    
                    if isinstance(chat_invite, (types.ChatInviteAlready, types.ChatInvitePeek)):
                        return chat_invite.chat
                    
                raise ChatNotAvailableError()
            except (
                errors.ChannelInvalidError, 
                errors.ChannelPrivateError, 
                ### ------------------------
                errors.InviteHashEmptyError, 
                errors.InviteHashExpiredError, 
                errors.InviteHashInvalidError, 
                ### ------------------------
                ChatNotAvailableError, 
                ClientNotAvailableError
            ):
                pass
        else:
            raise ChatNotAvailableError()
        
    async def join_via_phone(self, phone):
        client = await phone.new_client(loop=self.loop)
        
        try:
            await client(
                functions.channels.JoinChannelRequest(channel=self.chat.username) 
                    if self.chat.hash is None else 
                        functions.messages.ImportChatInviteRequest(hash=self.chat.hash)
            )
        except (
            ValueError,
            ### -----------------------------
            errors.UsernameNotOccupiedError,
            ### -----------------------------
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
            return
        except errors.FloodWaitError as ex:
            logging.error(f"Chat {self.chat.id} wiring for phone {phone.id} must wait. Exception: {ex}.")
            
            await asyncio.sleep(ex.seconds)
            
            await self.join_via_phone(phone)
        
    async def join_via_phones(self, available_phones, new_phones):
        to_join = list(
            sorted(
                [available_phones[k] for k in list(set(available_phones) - set(new_phones))], 
                key=lambda p: p.chats_count
            )
        )
        
        logging.debug(f"{len(to_join)} phones ready for joining in chat {self.chat.id}.")
        
        for phone in to_join:
            try:
                await self.join_via_phone(phone)
            except (ChatNotAvailableError, ClientNotAvailableError) as ex:
                logging.error(f"Chat {self.chat.id} not available for phone {phone.id}. Exception: {ex}.")
                
                del available_phones[phone.id]
                
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                logging.info(f"Phone {phone.id} succesfully wired with chat {self.chat.id}.")
                
                new_phones[phone.id] = phone
                
                if len(new_phones.items()) >= 3:
                    logging.debug(f"Wired phones limit reached for chat {self.chat.id}.")
                    
                    break
                
                await asyncio.sleep(random.randint(2, 5))
        
        return available_phones, new_phones
            
    async def async_run(self):
        if len(self.chat.available_phones) == 0:
            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
        else:
            available_phones = dict([(p.id, p) for p in self.chat.available_phones])
            new_phones = dict([(p.id, p) for p in self.chat.phones])
            
            logging.debug(f"Chat {self.chat.id} has {len(available_phones.items())} available phones.")
            logging.debug(f"Chat {self.chat.id} has {len(new_phones.items())} wired phones.")
            
            if len(new_phones.items()) >= 3 or len(available_phones.items()) <= len(new_phones.items()):
                new_phones = await self.check_phones(new_phones)
            elif len(new_phones.items()) < 3:
                available_phones, new_phones = await self.join_via_phones(available_phones, new_phones)
                
            new_chat = { 'id': self.chat.id }
            
            if len(available_phones.items()) != len(self.chat.available_phones):
                logging.info(f"Chat {self.chat.id} list of available phones changed. Now it\'s {len(available_phones.items())}.")
                
                new_chat['availablePhones'] = [{ 'id': id } for id in available_phones.keys()] 
                
            if len(new_phones.items()) != len(self.chat.phones) or \
                any(x.id != y.id for x, y in zip(new_phones.values(), self.chat.phones)):
                logging.info(f"Chat {self.chat.id} list of wired phones changed. Now it\'s {len(new_phones.items())}.")
                
                new_chat['phones'] = [{ 'id': id } for id in new_phones.keys()] 
                
            if len(available_phones.items()) == 0 or len(new_phones.items()) == 0:
                new_chat['isAvailable'] = False
            else:
                try:
                    tg_chat = await self.get_tg_chat(new_phones)
                except ChatNotAvailableError:
                    new_chat['isAvailable'] = False
                else:
                    if self.chat.internal_id == None:
                        logging.info(f"Chat {self.chat.id} internal id getted.")
                        
                        new_chat['internalId'] = tg_chat.id
                    
                    if self.chat.title == None:
                        logging.info(f"Chat {self.chat.id} title getted.")
                        
                        new_chat['title'] = tg_chat.title
            
            if len(new_chat.items()) > 1:
                ApiProcessor().set('chat', new_chat)
                
        self.chat.chat_thread = None

    def run(self):
        asyncio.run(self.async_run())
