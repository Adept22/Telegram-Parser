import multiprocessing, asyncio, logging, telethon
import exceptions

class JoinChatProcess(multiprocessing.Process):
    def __init__(self, phone):
        multiprocessing.Process.__init__(self, name=f'JoinChatProcess-{phone.id}', daemon=True)
        
        self.lock = multiprocessing.Lock()
        
        self.phone = phone
        
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def async_run(self, chat):
        if len(chat.phones) >= 3:
            return

        try:
            client = await self.phone.new_client(loop=self.loop)
        except exceptions.ClientNotAvailableError as ex:
            logging.error(f"Chat {chat.id} not available for phone {self.phone.id}.")
            logging.exception(ex)

            chat.remove_available_phone(self.phone)
            chat.remove_phone(self.phone)

            return
        else:
            while True:
                try:
                    tg_chat = await chat.join_channel(client)
                except telethon.errors.FloodWaitError as ex:
                    logging.error(f"Chat {chat.id} wiring for phone {self.phone.id} must wait {ex.seconds}.")

                    await asyncio.sleep(ex.seconds)

                    continue
                except exceptions.ChatNotAvailableError as ex:
                    logging.error(f"Chat {chat.id} not available for phone {self.phone.id}.")
                    logging.exception(ex)

                    chat.is_available = False

                    break
                except (
                    ### -----------------------------
                    telethon.errors.ChannelsTooMuchError,
                    telethon.errors.SessionPasswordNeededError
                ) as ex:
                    logging.error(f"Chat {chat.id} not available for phone {self.phone.id}.")
                    logging.exception(ex)

                    chat.remove_available_phone(self.phone)
                    chat.remove_phone(self.phone)

                    break
                else:
                    logging.info(f"Phone {self.phone.id} succesfully wired with chat {chat.id}.")

                    if chat.internal_id == None:
                        chat.internal_id = tg_chat.id

                    if chat.title == None:
                        chat.title = tg_chat.title

                    if chat.date != tg_chat.date.isoformat():
                        chat.date = tg_chat.date.isoformat()

                    chat.add_phone(self.phone)

                    break

    def run(self):
        self.phone.init_event.wait()
        
        while True:
            chat = self.phone.joining_queue.get()

            with self.lock:
                asyncio.run(self.async_run(chat))

            self.phone.joining_queue.task_done()