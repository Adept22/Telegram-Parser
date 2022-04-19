import threading, asyncio, logging, telethon
import entities, exceptions

class JoinChatsThread(threading.Thread):
    def __init__(self, phone: 'entities.TypePhone'):
        threading.Thread.__init__(self, name=f'JoinChatsThread-{phone.id}', daemon=True)

        self.phone = phone
        self.loop = asyncio.new_event_loop()
        self.lock = threading.Lock()
        
        asyncio.set_event_loop(self.loop)
        
    async def async_run(self, chat: 'entities.TypeChat', chat_phone: 'entities.TypeChatPhone'):
        if len(chat.phones) >= 3:
            return

        try:
            client = await self.phone.new_client(loop=self.loop)
        except exceptions.ClientNotAvailableError as ex:
            logging.error(f"Chat {chat.id} not available for phone {self.phone.id}.")

            return
            
        while True:
            try:
                if chat.hash is None:
                    updates = await client(telethon.functions.channels.JoinChannelRequest(chat.username))
                    tg_chat: 'telethon.types.TypeChat' = updates.chats[0]
                else:
                    try:
                        updates = await client(telethon.functions.messages.ImportChatInviteRequest(chat.hash))
                    except telethon.errors.UserAlreadyParticipantError as ex:
                        invite = await client(telethon.functions.messages.CheckChatInviteRequest(chat.hash))
                        tg_chat = invite.chat if invite.chat else invite.channel
                    else:
                        tg_chat = updates.chats[0]
            except telethon.errors.FloodWaitError as ex:
                logging.warning(f"Chat {chat.id} wiring for phone {self.phone.id} must wait {ex.seconds}.")

                await asyncio.sleep(ex.seconds)

                continue
            except(
                telethon.errors.ChannelsTooMuchError, 
                telethon.errors.SessionPasswordNeededError
            ) as ex:
                logging.error(f"Chat {chat.id} not available for phone {self.phone.id}. Exception {ex}")

                break
            except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                logging.critical(f"Chat {chat.id} not available.")

                chat.isAvailable = False
                chat.save()

                break
            else:
                logging.info(f"Phone {self.phone.id} succesfully wired with chat {chat.id}.")

                internal_id = telethon.utils.get_peer_id(tg_chat)

                if chat._internalId != internal_id:
                    chat.internalId = internal_id

                if chat.title != tg_chat.title:
                    chat.title = tg_chat.title

                if chat.date != tg_chat.date.isoformat():
                    chat.date = tg_chat.date.isoformat()

                chat_phone.isUsing = True
                chat_phone.save()

                chat.phones.append(chat_phone)

                break

    def run(self):
        while True:
            args: 'tuple[entities.TypeChat, entities.TypeChatPhone]' = self.phone._join_queue.get()

            with self.lock:
                asyncio.run(self.async_run(args[0], args[1]))

            self.phone._join_queue.task_done()