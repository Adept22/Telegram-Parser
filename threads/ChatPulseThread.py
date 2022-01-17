import threading
import asyncio
import random
import logging

from telethon import errors, types

from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.ClientNotAvailableError import ClientNotAvailableError

class ChatPulseThread(threading.Thread):
    def __init__(self, chat, phones):
        threading.Thread.__init__(self, name=f'ChatPulseThread-{chat.id}')
        
        self.new_chat = None
        self.new_phones = dict([(p.id, p) for p in phones])
        
        self.loop = asyncio.new_event_loop()
        self.chat = chat
        
        asyncio.set_event_loop(self.loop)
            
    async def async_run(self):
        logging.debug(f"{len(self.new_phones.items())} phones initially wired with chat {self.chat.id}.")
        
        for id, phone in self.new_phones.items():
            try:
                client = await phone.new_client(loop=self.loop)
                logging.debug(f"Try to get chat {self.chat.id} for check pulse using phone {id}.")
                
                self.new_chat = await client.get_entity(types.PeerChannel(channel_id=self.chat.internal_id))
                logging.info(f"Chat {self.chat.id} getted from Telethone by phone {id}.")
            except (
                ClientNotAvailableError, 
                ChatNotAvailableError, 
                errors.ChannelInvalidError,
                errors.ChannelPrivateError,
                errors.NeedChatInvalidError,
                errors.ChatIdInvalidError,
                errors.PeerIdInvalidError
            ) as ex:
                logging.error(f"Chat or channel {self.chat.id} not available for phone {id} problem. Exception: {ex}.")
                
                del self.new_phones[id]
        
            await asyncio.sleep(random.randint(2, 5))

    def run(self):
        asyncio.run(self.async_run())
        
    def join(self, *args):
        threading.Thread.join(self, *args)
        
        return self.new_chat, list(self.new_phones.values())