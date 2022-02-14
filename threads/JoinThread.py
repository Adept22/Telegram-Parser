import threading
import asyncio
import logging

from telethon import errors

from processors.ApiProcessor import ApiProcessor
from errors.ClientNotAvailableError import ClientNotAvailableError
from threads.KillableThread import KillableThread

class JoinThread(KillableThread):
    def __init__(self, phone):
        threading.Thread.__init__(self, name=f'JoinThread-{phone.id}')
        self.lock = threading.Lock()
        
        self.phone = phone
        
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
            
    async def async_run(self, chat):
        with chat.join_lock:
            if len(chat.phones) >= 3:
                logging.debug(f"Wired phones limit reached for chat {chat.id}.")
                
                return

            new_chat = { 'id': chat.id }

            available_phones = dict([(p.id, p) for p in chat.available_phones])
            phones = dict([(p.id, p) for p in chat.phones])

            try:
                client = await self.phone.new_client(loop=self.loop)

                await chat.join_channel(client)
            except errors.FloodWaitError as ex:
                logging.error(f"Chat {chat.id} wiring for phone {self.phone.id} must wait. Exception: {ex}.")
                
                await asyncio.sleep(ex.seconds)
            except (
                ClientNotAvailableError, 
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

                if len(available_phones.items()) != len(chat.available_phones):
                    logging.info(f"Chat {chat.id} list of available phones changed. Now it\'s {len(available_phones.items())}.")
                    
                    chat.available_phones = [{'id': id} for id in available_phones.keys()]
                    new_chat['availablePhones'] = [{ 'id': id } for id in available_phones.keys()]
                    
                if len(phones.items()) != len(chat.phones) or \
                    any(x.id != y.id for x, y in zip(phones.values(), chat.phones)):
                    logging.info(f"Chat {chat.id} list of wired phones changed. Now it\'s {len(phones.items())}.")

                    chat.phones = [{'id': id} for id in phones.keys()]
                    new_chat['phones'] = [{ 'id': id } for id in phones.keys()]

                if len(new_chat.items()) > 1:
                    ApiProcessor().set('chat', new_chat)

    def run(self):
        while True:
            args, kwargs = self.phone.joining_queue.get()

            with self.lock:
                asyncio.run(self.async_run(*args, **kwargs))

            self.phone.joining_queue.task_done()