import multiprocessing, asyncio, logging, random, telethon
import entities, exceptions, helpers

class ChatMediaProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat'):
        multiprocessing.Process.__init__(self, name=f'ChatMediaProcess-{chat.id}', daemon=True)

        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    async def async_run(self):
        if len(self.chat.phones) == 0:
            logging.warning(f"No phones for chat {self.chat.id}.")

            return
            
        for phone in self.chat.phones:
            try:
                client = await phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.error(f"Phone {phone.id} client not available.")

                self.chat.remove_phone(phone)
                self.chat.save()
                
                continue
            
            try:
                tg_chat = await helpers.get_entity(client, self.chat)
            except exceptions.ChatNotAvailableError as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}.")

                self.chat.isAvailable = False
                self.chat.save()

                break
            else:
                new_internal_id = telethon.utils.get_peer_id(tg_chat)
                
                if self.chat.internalId != new_internal_id:
                    logging.info(f"Chat {self.chat.id} internal ID changed. Old ID {self.chat.internalId}. New ID {new_internal_id}.")
                    
                    self.chat.internalId = new_internal_id

                    self.chat.save()
                
            try:
                async for photo in client.iter_profile_photos(entity=tg_chat):
                    photo: 'telethon.types.TypePhoto'

                    media = entities.ChatMedia(internalId=photo.id, chat=self.chat, date=photo.date.isoformat())

                    try:
                        media.save()
                    except exceptions.RequestException as ex:
                        logging.error(f"Can\'t save chat {self.chat.id} media. Exception: {ex}.")
                    else:
                        logging.info(f"Sucessfuly saved chat {self.chat.id} media.")

                        try:
                            await media.upload(client, photo, photo.sizes[-2])
                        except exceptions.RequestException as ex:
                            logging.error(f"Can\'t upload chat {self.chat.id} media. Exception: {ex}.")
                        else:
                            logging.info(f"Sucessfuly uploaded chat {self.chat.id} media.")
            except telethon.errors.RPCError as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}. Exception {ex}")
                
                continue
            else:
                break
        else:
            logging.error(f"Can't get chat {self.chat.id} medias.")

    def run(self):
        asyncio.run(self.async_run())
