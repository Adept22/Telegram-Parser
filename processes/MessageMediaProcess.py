import multiprocessing, asyncio, logging, telethon
import entities, exceptions

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from telethon import TelegramClient

class MessageMediaProcess(multiprocessing.Process):
    def __init__(self, phone: 'entities.TypePhone', message: 'entities.TypeMessage', tg_message: 'telethon.types.TypeMessage'):
        multiprocessing.Process.__init__(self, name=f"MessageMediaProcess-{message.id}", daemon=True)
        
        self.phone = phone
        self.message = message
        self.tg_message = tg_message

        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
    
    async def file_download(self, client: 'TelegramClient', tg_media, size):
        media = entities.MessageMedia(internalId=tg_media.id, message=self.message, date=tg_media.date.isoformat())
        
        try:
            media.save()
        except exceptions.RequestException as ex:
            logging.error(f"Can\'t save message {self.message.id} media. Exception: {ex}.")
        else:
            logging.info(f"Sucessfuly saved message {self.message.id} media.")

            try:
                await media.upload(client, tg_media, size)
            except exceptions.RequestException as ex:
                logging.error(f"Can\'t upload message {self.message.id} media. Exception: {ex}.")
            else:
                logging.info(f"Sucessfuly uploaded message {self.message.id} media.")

    async def async_run(self):
        logging.debug(f"Try to save message '{self.message.id}' media.")

        try:
            client = await self.phone.new_client(loop=self.loop)
        except exceptions.ClientNotAvailableError as ex:
            logging.error(f"Phone {self.phone.id} client not available.")
            
            return

        if isinstance(self.tg_message.media, telethon.types.MessageMediaPoll):
            pass
        elif isinstance(self.tg_message.media, telethon.types.MessageMediaVenue):
            pass
        elif isinstance(self.tg_message.media, telethon.types.MessageMediaContact):
            pass
        elif isinstance(self.tg_message.media, telethon.types.MessageMediaPhoto):
            await self.file_download(client, self.tg_message.photo, self.tg_message.photo.sizes[-2])
        elif isinstance(self.tg_message.media, telethon.types.MessageMediaDocument):
            await self.file_download(client, self.tg_message.document, self.tg_message.document.size)
        
    def run(self):
        asyncio.run(self.async_run())