import multiprocessing, setproctitle, asyncio, logging, typing, telethon
import entities, exceptions, helpers

if typing.TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.events.chataction import ChatAction

class ChatProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat', manager):
        multiprocessing.Process.__init__(self, name=f'ChatProcess-{chat.id}', daemon=True)

        setproctitle.setproctitle(self.name)

        self.chat = chat
        self.manager = manager
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    async def async_run(self):
        chat_phones = helpers.get_all('telegram/chat-phone', { "chat": { "id": self.chat.id }})
        chat_phones = filter(lambda chat_phone: chat_phone["phone"]["id"] in self.manager, chat_phones)

        for chat_phone in filter(lambda chat_phone: chat_phone["isUsing"], chat_phones):
            chat_phone = entities.ChatPhone(**chat_phone, chat=self.chat, phone=self.manager[chat_phone["phone"]["id"]])

            self.chat.phones.append(chat_phone)

        if len(self.chat.phones) < 3 and len(chat_phones) > len(self.chat.phones):
            for chat_phone in filter(lambda chat_phone: not chat_phone["isUsing"], chat_phones):
                self.manager[chat_phone["phone"]["id"]].join_chat(self)
            
        for chat_phone in self.chat.phones:
            chat_phone: 'entities.TypeChatPhone'

            try:
                client: 'TelegramClient' = await chat_phone.phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.critical(f"Chat phone {chat_phone.id} client not available. Exception: {ex}")

                self.chat.phones.remove(chat_phone)
                
                continue

            logging.error(f"Try get TG entity of chat {self.chat.id}.")

            try:
                tg_chat = await helpers.get_entity(client, self.chat)
            except exceptions.ChatNotAvailableError as ex:
                logging.error(f"Can\'t get chat TG entity {self.chat.id} using chat phone {chat_phone.id}. Exception {ex}")

                self.chat.phones.remove(chat_phone)

                continue
            else:
                logging.debug(f"TG entity of chat {self.chat.id} received.")

                new_internal_id = telethon.utils.get_peer_id(tg_chat)
                
                if self.chat._internalId != new_internal_id:
                    old_internal_id = self.chat._internalId
                    self.chat.internalId = new_internal_id

                    try:
                        self.chat.save()
                    except exceptions.UniqueConstraintViolationError:
                        logging.critical(f"Chat with internal id {new_internal_id} exist. Current chat {self.chat.id}")

                        self.chat.internalId = old_internal_id
                        self.chat.isAvailable = False
                        
                        self.chat.save()
                else:
                    async def handle_event(event: 'ChatAction.Event'):
                        if event.new_title:
                            self.chat.title = event.new_title

                            try:
                                self.chat.save()
                            except exceptions.RequestException:
                                return

                    client.add_event_handler(handle_event, telethon.events.chataction.ChatAction(chats=self.chat.internalId))
                
                break
        else:
            logging.error(f"Can't initialize chat {self.chat.id}.")

    def run(self):
        asyncio.run(self.async_run())
