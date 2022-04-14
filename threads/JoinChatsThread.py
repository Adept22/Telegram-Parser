import queue, threading, asyncio, logging, telethon
import entities, exceptions, helpers

class JoinChatsThread(threading.Thread):
    def __init__(self, phone: 'entities.TypePhone'):
        threading.Thread.__init__(self, name=f'JoinChatsThread-{phone.id}', daemon=True)
        
        self.phone = phone
        self.loop = asyncio.new_event_loop()
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        
        asyncio.set_event_loop(self.loop)
        
    async def async_run(self, chat: 'entities.TypeChat'):
        if len(chat.phones) >= 3:
            return

        try:
            client = await self.phone.new_client(loop=self.loop)
        except exceptions.ClientNotAvailableError as ex:
            logging.error(f"Chat {chat.id} not available for phone {self.phone.id}.")

            chat.remove_available_phone(self.phone)
            chat.remove_phone(self.phone)
        else:
            while True:
                try:
                    try:
                        updates = await client(
                            telethon.functions.channels.JoinChannelRequest(channel=chat.username) 
                                if chat.hash is None else 
                                    telethon.functions.messages.ImportChatInviteRequest(hash=chat.hash)
                        )
                    except telethon.errors.UserAlreadyParticipantError as ex:
                        tg_chat = await helpers.get_entity(client, chat)
                    except (ValueError, telethon.errors.RPCError) as ex:
                        raise exceptions.ChatNotAvailableError(ex)
                    else:
                        tg_chat = updates.chats[0]
                except telethon.errors.FloodWaitError as ex:
                    logging.error(f"Chat {chat.id} wiring for phone {self.phone.id} must wait {ex.seconds}.")

                    await asyncio.sleep(ex.seconds)

                    continue
                except exceptions.ChatNotAvailableError as ex:
                    logging.error(f"Chat {chat.id} not available for phone {self.phone.id}.")

                    chat.isAvailable = False

                    break
                except telethon.errors.RPCError as ex:
                    logging.error(f"Chat {chat.id} not available for phone {self.phone.id}. Exception {ex}")

                    chat.remove_available_phone(self.phone)
                    chat.remove_phone(self.phone)

                    break
                else:
                    logging.info(f"Phone {self.phone.id} succesfully wired with chat {chat.id}.")

                    internal_id = telethon.utils.get_peer_id(tg_chat)

                    if chat.internalId != internal_id:
                        chat.internalId = internal_id
                        
                    type = helpers.get_type(tg_chat)

                    if chat.type != type:
                        chat.type = type

                    if chat.title != tg_chat.title:
                        chat.title = tg_chat.title

                    if chat.date != tg_chat.date.isoformat():
                        chat.date = tg_chat.date.isoformat()

                    chat.add_phone(self.phone)

                    break

        chat.save()

    def run(self):
        while True:
            chat: 'entities.TypeChat' = self.queue.get()

            with self.lock:
                asyncio.run(self.async_run(chat))

            self.queue.task_done()