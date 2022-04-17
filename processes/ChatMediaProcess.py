import os, multiprocessing, asyncio, logging, telethon
import entities, exceptions, helpers
from services.PhonesManager import PhonesManager

class ChatMediaProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat'):
        multiprocessing.Process.__init__(self, name=f'ChatMediaProcess-{chat.id}', daemon=True)

        os.nice(10)

        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    async def async_run(self):
        for phone in self.chat.phones:
            try:
                client = await phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.critical(f"Phone {phone.id} client not available. Exception: {ex}")

                self.chat.phones.remove(phone)
                
                continue
            
            try:
                async for photo in client.iter_profile_photos(entity=self.chat.internalId):
                    photo: 'telethon.types.TypePhoto'

                    media = entities.ChatMedia(internalId=photo.id, chat=self.chat, date=photo.date.isoformat())

                    try:
                        media.save()
                    except exceptions.RequestException as ex:
                        logging.error(f"Can't save chat {self.chat.id} media. Exception: {ex}.")
                    else:
                        logging.info(f"Sucessfuly saved chat {self.chat.id} media.")

                        size = photo.sizes[-2]

                        try:
                            await media.upload(
                                client, 
                                telethon.types.InputPhotoFileLocation(
                                    id=photo.id,
                                    access_hash=photo.access_hash,
                                    file_reference=photo.file_reference,
                                    thumb_size=size.type
                                ), 
                                size.size
                            )
                        except exceptions.RequestException as ex:
                            logging.error(f"Can't upload chat {self.chat.id} media. Exception: {ex}.")
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
