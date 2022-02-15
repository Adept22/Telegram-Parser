import threading
import asyncio
import logging

from telethon import errors

from errors.ClientNotAvailableError import ClientNotAvailableError
from errors.ChatNotAvailableError import ChatNotAvailableError
from threads.KillableThread import KillableThread

class JoinThread(KillableThread):
    def __init__(self, phone):
        threading.Thread.__init__(self, name=f'JoinThread-{phone.id}')
        self.daemon = True
        self.lock = threading.Lock()
        
        self.phone = phone
        
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def async_run(self, chat):
        with chat.phones_lock:
            if len(chat.phones) >= 3:
                return

            try:
                client = await self.phone.new_client(loop=self.loop)

                tg_chat = await chat.join_channel(client)
            except errors.FloodWaitError as ex:
                logging.error(f"Chat {chat.id} wiring for phone {self.phone.id} must wait. Exception: {ex}.")

                await asyncio.sleep(ex.seconds)

                return await self.join_channel(chat)
            except (
                ClientNotAvailableError,
                ChatNotAvailableError,
                ### -----------------------------
                errors.ChannelsTooMuchError,
                errors.SessionPasswordNeededError
            ) as ex:
                logging.error(f"Chat {chat.id} not available for phone {self.phone.id}. Exception: {ex}.")

                chat.remove_available_phone(self.phone)
                chat.remove_phone(self.phone)
            else:
                logging.info(f"Phone {self.phone.id} succesfully wired with chat {chat.id}.")

                if chat.internal_id == None:
                    chat.internal_id = tg_chat.id

                if chat.title == None:
                    chat.title = tg_chat.title

                chat.add_phone(self.phone)

    def run(self):
        self.phone.init_event.wait()
        
        while True:
            chat = self.phone.joining_queue.get()

            with self.lock:
                asyncio.run(self.async_run(chat))

            self.phone.joining_queue.task_done()