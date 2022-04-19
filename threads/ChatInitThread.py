import threading, asyncio, logging, telethon
import globalvars, entities, exceptions, helpers

class ChatInitThread(threading.Thread):
    def __init__(self, chat: 'entities.TypeChat'):
        threading.Thread.__init__(self, name=f'ChatInitThread-{chat.id}', daemon=True)

        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    async def async_run(self):
        chat_phones = helpers.get_all('telegram/chat-phone', { "chat": { "id": self.chat.id }})
        chat_phones = list(filter(lambda chat_phone: chat_phone["phone"]["id"] in globalvars.phones_manager, chat_phones))
        chat_phones = [entities.ChatPhone(id=chat_phone["id"], chat=self.chat, phone=globalvars.phones_manager[chat_phone["phone"]["id"]], isUsing=chat_phone["isUsing"]) for chat_phone in chat_phones]
        
        using_phones = list(filter(lambda chat_phone: chat_phone.isUsing, chat_phones))
        for i, chat_phone in enumerate(using_phones):
            """Appending using phones"""
            try:
                client = await chat_phone.phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.critical(f"Chat phone {chat_phone.id} client not available. Exception: {ex}")

                del using_phones[i]
                
                continue

            logging.debug(f"Try get TG entity of chat {self.chat.id} by chat phone {chat_phone.id}.")

            try:
                tg_chat = await helpers.get_entity(client, self.chat)
            except exceptions.ChatNotAvailableError as ex:
                logging.error(f"Can\'t get chat TG entity {self.chat.id} using chat phone {chat_phone.id}. Exception {ex}")

                chat_phone.isUsing = False
                chat_phone.save()
                
                del using_phones[i]

                continue
            else:
                logging.debug(f"TG entity of chat {self.chat.id} received by chat phone {chat_phone.id}.")

                new_internal_id = telethon.utils.get_peer_id(tg_chat)
                
                if self.chat._internalId != new_internal_id:
                    logging.info(f"Chat {self.chat.id} internal id changed.")
                    
                    old_internal_id = self.chat._internalId
                    self.chat.internalId = new_internal_id

                    try:
                        self.chat.save()
                    except exceptions.UniqueConstraintViolationError:
                        logging.critical(f"Chat with internal id {new_internal_id} exist. Current chat {self.chat.id}")

                        self.chat.internalId = old_internal_id
                        self.chat.isAvailable = False
                        
                        self.chat.save()
                
                self.chat.phones.append(chat_phone)

        if len(self.chat.phones) < 3 and len(chat_phones) > len(self.chat.phones):
            not_using_phones = list(filter(lambda chat_phone: not chat_phone.isUsing, chat_phones))
            for chat_phone in not_using_phones:
                globalvars.phones_manager[chat_phone.phone.id].join_chat(self.chat, chat_phone)
            
        globalvars.chats_manager[self.chat.id] = self.chat

        logging.debug(f'Chats in manager {len(globalvars.chats_manager)}')

    def run(self):
        asyncio.run(self.async_run())
