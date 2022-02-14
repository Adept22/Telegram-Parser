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
        self.daemon = True
        
        self.chat = chat
        
        self.exit_event = threading.Event()
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
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
        
    async def async_run(self):
        while True:                                
            if len(self.chat.available_phones) == 0:
                if self.chat.init_event.is_set():
                    self.chat.init_event.clear()

                ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
                
                break
            else:
                logging.debug(f"Chat {self.chat.id} has {len(self.chat.available_phones)} available phones.")
                logging.debug(f"Chat {self.chat.id} has {len(self.chat.phones)} wired phones.")
                
                if len(self.chat.phones) > 0 and self.chat.internal_id != None:
                    if not self.chat.init_event.is_set():
                        self.chat.init_event.set()
                        
                if (len(self.chat.phones) >= 3 or len(self.chat.available_phones) <= len(self.chat.phones)):
                    for phone in self.chat.phones:
                        phone.pulse_queue.put(self.chat)
                elif len(self.chat.phones) < 3 and len(self.chat.available_phones) > len(self.chat.phones):
                    available_phones = dict([(p.id, p) for p in self.chat.available_phones])
                    phones = dict([(p.id, p) for p in self.chat.phones])
                    
                    logging.debug(f"{len(available_phones) - len(phones)} phones ready for joining in chat {self.chat.id}.")
                    
                    for id in list(set(available_phones) - set(phones)):
                        available_phones[id].joining_queue.put(self.chat)
            
            await asyncio.sleep(10)

    def run(self):
        asyncio.run(self.async_run())
