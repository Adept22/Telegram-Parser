import os, multiprocessing, setproctitle, asyncio, logging, typing, telethon
import entities, exceptions, helpers
from services import PhonesManager

if typing.TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.events.chataction import ChatAction

class ChatProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat'):
        multiprocessing.Process.__init__(self, name=f'ChatProcess-{chat.id}', daemon=True)

        setproctitle.setproctitle(self.name)

        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)


    async def async_run(self):
        for phone in helpers.get_all('telegram/chat-available-phone', { "chat": { "id": self.chat.id }, "parser": { "id": os.environ['PARSER_ID'] }}):
            
            if phone["id"] in PhonesManager:
                self.chat.available_phones.append(PhonesManager[phone["id"]])

        for phone in helpers.get_all('telegram/chat-phone', { "chat": { "id": self.chat.id }, "parser": { "id": os.environ['PARSER_ID'] }}):
            if phone["id"] in PhonesManager:
                self.chat.available_phones.append(PhonesManager[phone["id"]])
        
        if len(self.chat.phones) < 3 and len(self.chat.availablePhones) > len(self.chat.phones):
            # Using range for avoid process blocking
            a_ps: 'dict[str, entities.TypePhone]' = dict([(self.chat.availablePhones[i].id, self.chat.availablePhones[i]) for i in range(0, len(self.chat.availablePhones))])
            ps: 'dict[str, entities.TypePhone]' = dict([(self.chat.phones[i].id, self.chat.phones[i]) for i in range(0, len(self.chat.phones))])

            for id in list(set(a_ps) - set(ps)):
                a_ps[id].join_chat(self)
            
        for phone in self.chat.phones:
            try:
                client: 'TelegramClient' = await phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.critical(f"Phone {phone.id} client not available. Exception: {ex}")

                self.chat.phones.remove(phone)
                self.chat.save()
                
                continue

            logging.error(f"Try get TG entity of chat {self.chat.id}.")

            try:
                tg_chat = await helpers.get_entity(client, self.chat)
            except exceptions.ChatNotAvailableError as ex:
                logging.error(f"Can\'t get chat TG entity {self.chat.id} using phone {phone.id}. Exception {ex}")

                self.chat.phones.remove(phone)
                self.chat.availablePhones.remove(phone)
                self.chat.save()

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
