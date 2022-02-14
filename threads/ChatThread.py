from multiprocessing.connection import wait
import threading
import asyncio
import random
import logging

from telethon import functions, errors, types

from processors.ApiProcessor import ApiProcessor
from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.ClientNotAvailableError import ClientNotAvailableError
from threads.KillableThread import KillableThread

class ChatThread(KillableThread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'ChatThread-{chat.id}')
        
        self.chat = chat
        
        self.exit_event = threading.Event()
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
            
    async def get_tg_chat(self, phone):
        client = await phone.new_client(loop=self.loop)
        
        try:
            if self.chat.internal_id != None:
                try:
                    return await client.get_entity(types.PeerChannel(channel_id=self.chat.internal_id))
                except:
                    pass

            if self.chat.hash != None:
                chat_invite = await client(functions.messages.CheckChatInviteRequest(hash=self.chat.hash))
                
                if isinstance(chat_invite, (types.ChatInviteAlready, types.ChatInvitePeek)):
                    return chat_invite.chat
            elif self.chat.username != None:
                return await client.get_entity(self.chat.username)
            
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
        
    async def check_phones(self, phones):
        new_phones = dict(phones)
        
        for phone in phones.values():
            try:
                await self.get_tg_chat(phone)
            except errors.FloodWaitError as ex:
                logging.error(f"Get chat {self.chat.id} by phone {phone.id} must wait. Exception: {ex}.")
                
                continue
            except (ClientNotAvailableError, ChatNotAvailableError) as ex:
                logging.error(f"Chat {self.chat.id} not available for phone {phone.id}. Exception: {ex}.")
                
                del new_phones[phone.id]
            else:
                logging.info(f"Chat {self.chat.id} available for phone {phone.id}.")
                
                await asyncio.sleep(random.randint(2, 5))
        
        return new_phones
        
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
        
    async def join_via_phones(self, available_phones, new_phones):
        to_join = list(
            sorted(
                [available_phones[k] for k in list(set(available_phones) - set(new_phones))], 
                key=lambda p: p.chats_count
            )
        )
        
        logging.debug(f"{len(to_join)} phones ready for joining in chat {self.chat.id}.")
    
        try:
            for phone in to_join:
                try:
                    await self.join_via_phone(phone)
                except errors.FloodWaitError as ex:
                    logging.error(f"Chat {self.chat.id} wiring for phone {phone.id} must wait. Exception: {ex}.")
                    
                    continue
                except (
                    ClientNotAvailableError, 
                    ### -----------------------------
                    errors.ChannelsTooMuchError, 
                    errors.SessionPasswordNeededError
                ) as ex:
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
        except ChatNotAvailableError as ex:
            logging.error(f"Chat {self.chat.id} not available. Exception: {ex}.")
            
            available_phones = {}
            new_phones = {}
        
        return available_phones, new_phones
            
    async def async_run(self):
        if len(self.chat.available_phones) == 0:
            if self.chat.run_event.is_set():
                self.chat.run_event.clear()

            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
        else:
            new_chat = { 'id': self.chat.id }

            available_phones = dict([(p.id, p) for p in self.chat.available_phones])
            phones = dict([(p.id, p) for p in self.chat.phones])
            
            logging.debug(f"Chat {self.chat.id} has {len(available_phones.items())} available phones.")
            logging.debug(f"Chat {self.chat.id} has {len(phones.items())} wired phones.")
            
            if (len(phones.items()) >= 3 or len(available_phones.items()) <= len(phones.items())):
                phones = await self.check_phones(phones)
            elif len(phones.items()) < 3:
                available_phones, phones = await self.join_via_phones(available_phones, phones)
            


            if len(available_phones.items()) != len(self.chat.available_phones):
                logging.info(f"Chat {self.chat.id} list of available phones changed. Now it\'s {len(available_phones.items())}.")
                
                self.chat.available_phones = [{'id': id} for id in available_phones.keys()]
                new_chat['availablePhones'] = [{ 'id': id } for id in available_phones.keys()]
                
            if len(phones.items()) != len(self.chat.phones) or \
                any(x.id != y.id for x, y in zip(phones.values(), self.chat.phones)):
                logging.info(f"Chat {self.chat.id} list of wired phones changed. Now it\'s {len(phones.items())}.")

                self.chat.phones = [{'id': id} for id in phones.keys()]
                new_chat['phones'] = [{ 'id': id } for id in phones.keys()]


                
            
            if len(self.chat.available_phones) == 0 or len(self.chat.phones) == 0:
                if self.chat.run_event.is_set():
                    self.chat.run_event.clear()

                self.chat.is_available = False

                new_chat['isAvailable'] = False
            elif len(self.chat.phones) > 0:
                for phone in self.chat.phones:
                    try:
                        tg_chat = await self.get_tg_chat(phone)
                    except (ClientNotAvailableError, ChatNotAvailableError, errors.FloodWaitError):
                        continue
                    else:
                        if self.chat.internal_id == None:
                            logging.info(f"Chat {self.chat.id} internal id getted.")

                            self.chat.internal_id = tg_chat.id
                            new_chat['internalId'] = self.chat.internal_id
                        
                        if self.chat.title == None:
                            logging.info(f"Chat {self.chat.id} title getted.")

                            self.chat.title = tg_chat.title
                            new_chat['title'] = self.chat.title
                        
                        break

            if len(self.chat.phones) > 0 and self.chat.internal_id != None:
                if not self.chat.run_event.is_set():
                    self.chat.run_event.set()
            
            if len(new_chat.items()) > 1:
                ApiProcessor().set('chat', new_chat)
        
        await asyncio.sleep(60)

        await self.async_run()

    def run(self):
        asyncio.run(self.async_run())
