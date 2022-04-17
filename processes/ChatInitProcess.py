import os, multiprocessing, asyncio, logging, telethon
import entities, exceptions, helpers

class ChatInitProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat'):
        multiprocessing.Process.__init__(self, name=f'ChatInitProcess-{chat.id}', daemon=True)

        os.nice(10)

        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    async def async_run(self):
        if len(self.chat.phones) < 3 and len(self.chat.availablePhones) > len(self.chat.phones):
            # Using range for avoid process blocking
            a_ps: 'dict[str, entities.TypePhone]' = dict([(self.chat.availablePhones[i].id, self.chat.availablePhones[i]) for i in range(0, len(self.chat.availablePhones))])
            ps: 'dict[str, entities.TypePhone]' = dict([(self.chat.phones[i].id, self.chat.phones[i]) for i in range(0, len(self.chat.phones))])

            for id in list(set(a_ps) - set(ps)):
                a_ps[id].join_chat(self)
            
        for phone in self.chat.phones:
            try:
                client = await phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.critical(f"Phone {phone.id} client not available. Exception: {ex}")

                self.chat.phones.remove(phone)
                
                continue
            
            try:
                tg_chat = await helpers.get_entity(client, self.chat)
            except exceptions.ChatNotAvailableError as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}. Exception {ex}")

                self.chat.phones.remove(phone)
                self.chat.availablePhones.remove(phone)

                self.chat.save()

                continue
            else:
                new_internal_id = telethon.utils.get_peer_id(tg_chat)
                
                if self.chat._internalId != new_internal_id:
                    old_internal_id = self.chat._internalId
                    self.chat.internalId = new_internal_id

                    try:
                        self.chat.save()
                    except exceptions.UniqueConstraintViolationError:
                        logging.critical(f"Chat with internal id {self.chat._internalId} exist. Current chat {self.chat.id}")

                        self.chat.internalId = old_internal_id
                        self.chat.isAvailable = False
                        
                        self.chat.save()

                        break
        else:
            logging.error(f"Can't initialize chat {self.chat.id}.")

    def run(self):
        asyncio.run(self.async_run())
