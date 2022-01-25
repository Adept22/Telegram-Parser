import threading
import asyncio
import random
import logging

from telethon import errors, types

from processors.ApiProcessor import ApiProcessor
from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.ClientNotAvailableError import ClientNotAvailableError

class ChatPulseThread(threading.Thread):
    def __init__(self, chat, phones):
        threading.Thread.__init__(self, name=f'ChatPulseThread-{chat.id}')
        
        self.chat = chat
        self.phones = phones
        
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
            
    async def async_run(self):
        tg_chat = None
        new_phones = dict([(p.id, p) for p in self.phones])
        
        logging.debug(f"{len(new_phones.items())} phones initially wired with chat {self.chat.id}.")
        
        for phone in self.phones:
            try:
                client = await phone.new_client(loop=self.loop)
                
                logging.debug(f"Try to get chat {self.chat.id} for check pulse using phone {phone.id}.")
                
                tg_chat = await client.get_entity(types.PeerChannel(channel_id=self.chat.internal_id))
                
                logging.info(f"Chat {self.chat.id} getted from Telethone by phone {phone.id}.")
            except (
                ClientNotAvailableError, 
                ChatNotAvailableError, 
                errors.ChannelInvalidError,
                errors.ChannelPrivateError,
                errors.NeedChatInvalidError,
                errors.ChatIdInvalidError,
                errors.PeerIdInvalidError
            ) as ex:
                logging.error(f"Chat or channel {self.chat.id} not available for phone {phone.id} problem. Exception: {ex}.")
                
                del new_phones[phone.id]
            else:
                await asyncio.sleep(random.randint(2, 5))
        
        new_chat = { 'id': self.chat.id }
            
        if len(new_phones) != len(self.phones):
            logging.info(f"Chat {self.chat.id} list of phones changed...")
            
            new_chat['phones'] = [{ 'id': p.id } for p in new_phones]
            
        if tg_chat != None:
            if self.chat.internal_id != tg_chat.id:
                logging.info(f"Chat {self.chat.id} \'internalId\' changed...")
                
                new_chat['internalId'] = tg_chat.id
            
            if self.chat.title != tg_chat.title:
                logging.info(f"Chat {self.chat.id} \'title\' changed...")
                
                new_chat['title'] = tg_chat.title if self.chat.title == None else self.chat.title
                
        if len(new_phones) == 0:
            new_chat["isAvailable"] = False
                
        if len(new_chat.items()) > 1:
            ApiProcessor().set('chat', new_chat)

    def run(self):
        asyncio.run(self.async_run())