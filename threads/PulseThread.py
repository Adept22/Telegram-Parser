import threading
import asyncio
import logging

from telethon import errors

from errors.ClientNotAvailableError import ClientNotAvailableError
from errors.ChatNotAvailableError import ChatNotAvailableError
from threads.KillableThread import KillableThread

class PulseThread(KillableThread):
    def __init__(self, phone):
        threading.Thread.__init__(self, name=f'PulseThread-{phone.id}')
        self.daemon = True
        self.lock = threading.Lock()
        
        self.phone = phone
        
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def get_channel(self, chat, available_phones, phones):
        tg_chat = None
        
        try:
            client = await self.phone.new_client(loop=self.loop)

            tg_chat = await chat.get_internal_id(client)
        except errors.FloodWaitError as ex:
            logging.error(f"Chat {chat.id} wiring for phone {self.phone.id} must wait. Exception: {ex}.")
            
            await asyncio.sleep(ex.seconds)
            
            return await self.get_channel(chat, available_phones, phones)
        except (
            ClientNotAvailableError, 
            ChatNotAvailableError, 
            ### -----------------------------
            errors.ChannelsTooMuchError, 
            errors.SessionPasswordNeededError
        ) as ex:
            logging.error(f"Chat {chat.id} not available for phone {self.phone.id}. Exception: {ex}.")
            
            if self.phone.id in available_phones:
                del available_phones[self.phone.id]

            if self.phone.id in phones:
                del phones[self.phone.id]
        else:
            logging.info(f"Phone {self.phone.id} succesfully wired with chat {chat.id}.")
            
            if not self.phone.id in phones:
                phones[self.phone.id] = self.phone
                
        return tg_chat, available_phones, phones
            
    async def async_run(self, chat):
        with chat.phones_lock:
            available_phones = dict([(p.id, p) for p in chat.available_phones])
            phones = dict([(p.id, p) for p in chat.phones])
            
            tg_chat, available_phones, phones = await self.get_channel(chat, available_phones, phones)
            
            if tg_chat != None:
                if chat.internal_id == None:
                    chat.internal_id = tg_chat.id
                    
                if chat.title == None:
                    chat.title = tg_chat.title

            chat.available_phones = [{ 'id': id } for id in available_phones.keys()]
            chat.phones = [{ 'id': id } for id in phones.keys()]

    def run(self):
        self.phone.init_event.wait()
        
        while True:
            chat = self.phone.joining_queue.get()

            with self.lock:
                asyncio.run(self.async_run(chat))

            self.phone.joining_queue.task_done()