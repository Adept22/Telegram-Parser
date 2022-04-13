import multiprocessing, asyncio, logging, telethon
import entities, exceptions

class JoinChatsProcess(multiprocessing.Process):
    def __init__(self, phone: 'entities.TypePhone'):
        multiprocessing.Process.__init__(self, name=f'JoinChatsProcess-{phone.id}', daemon=True)
        
        self.phone = phone
        self.loop = asyncio.new_event_loop()
        self.lock = multiprocessing.Lock()
        
        asyncio.set_event_loop(self.loop)
        
    async def async_run(self, chat: 'entities.TypeChat'):
        if len(chat.phones) >= 3:
            return

        try:
            client = await self.phone.new_client(loop=self.loop)
        except exceptions.ClientNotAvailableError as ex:
            logging.error(f"Chat {chat.id} not available for phone {self.phone.id}.")
            logging.exception(ex)

            chat.remove_available_phone(self.phone)
            chat.remove_phone(self.phone)
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

                    chat.isAvailable = False

                    break
                except (
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

                    if chat.internalId == None:
                        chat.internalId = tg_chat.id

                    if chat.title != tg_chat.title:
                        chat.title = tg_chat.title

                    if chat.date != tg_chat.date.isoformat():
                        chat.date = tg_chat.date.isoformat()

                    chat.add_phone(self.phone)

                    break

        chat.save()

    def run(self):
        while True:
            chat: 'entities.TypeChat' = self.phone.joining_queue.get()

            with self.lock:
                asyncio.run(self.async_run(chat))

            self.phone.joining_queue.task_done()