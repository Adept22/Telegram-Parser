import threading
import asyncio
import logging
import random

from telethon import errors, types

from utils.bcolors import bcolors
from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.ClientNotAvailableError import ClientNotAvailableError
from utils.bcolors import bcolors

class ChatPulseThread(threading.Thread):
    def __init__(self, chat, phones):
        threading.Thread.__init__(self)
        
        self.new_chat = None
        self.new_phones = {}
        
        self.loop = asyncio.new_event_loop()
        self.chat = chat
        self.phones = phones
        
        asyncio.set_event_loop(self.loop)
            
    async def async_run(self):
        self.new_phones = dict([(p.id, p) for p in self.phones])
        
        print(f"{len(self.new_phones.items())} phones initially wired with chat {self.chat.id}.")
        logging.debug(f"{len(self.new_phones.items())} phones initially wired with chat {self.chat.id}.")
        
        for id, phone in self.new_phones.items():
            try:
                client = await phone.new_client(loop=self.loop)
                
                self.new_chat = await client.get_entity(types.PeerChannel(channel_id=self.chat.internal_id))
                
                print(f"Chat {self.chat.id} getted from Telethone by phone {id}.")
                logging.debug(f"Chat {self.chat.id} getted from Telethone by phone {id}.")
            except (
                ClientNotAvailableError, 
                ChatNotAvailableError, 
                errors.ChannelInvalidError,
                errors.ChannelPrivateError,
                errors.NeedChatInvalidError,
                errors.ChatIdInvalidError,
                errors.PeerIdInvalidError
            ) as ex:
                print(f"{bcolors.FAIL}Chat or channel {self.chat.id} not available for phone {id} problem. Exception: {ex}.{bcolors.ENDC}")
                logging.error(f"Chat or channel {self.chat.id} not available for phone {id} problem. Exception: {ex}.")
                
                del self.new_phones[id]
        
            await asyncio.sleep(random.randint(2, 5))

    def run(self):
        asyncio.run(self.async_run())
        
    def join(self, *args):
        threading.Thread.join(self, *args)
        
        return self.new_chat, list(self.new_phones.values())