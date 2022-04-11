import multiprocessing
import asyncio
import logging
from telethon import types
from entity.MessageMedia import MessageMedia

class MessageMediaProcess(multiprocessing.Process):
    def __init__(self, phone, message, tg_message):
        multiprocessing.Process.__init__(self, name=f"MessageMediaProcess-{message.id}", daemon=True)
        
        self.phone = phone
        self.message = message
        self.tg_message = tg_message

        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
    
    async def file_download(self, client, tg_media, size):
        try:
            media = MessageMedia(internalId=tg_media.id, message=self.message, date=tg_media.date.isoformat())
            media.save()
        except Exception as ex:
            logging.error(f"Can\'t save message {self.message.id} media. Exception: {ex}.")
            logging.exception(ex)
        else:
            logging.info(f"Sucessfuly saved message {self.message.id} media.")

            try:
                await media.upload(client, tg_media, size)
            except Exception as ex:
                logging.error(f"Can\'t upload message {self.message.id} media.")
                logging.exception(ex)
            else:
                logging.info(f"Sucessfuly uploaded message {self.message.id} media.")

    async def async_run(self):
        try:
            logging.debug(f"Try to save message '{self.message.id}' media.")

            client = await self.phone.new_client(loop=self.loop)
            
            if isinstance(self.tg_message.media, types.MessageMediaPoll):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaVenue):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaContact):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaPhoto):
                await self.file_download(client, self.tg_message.photo, self.tg_message.photo.sizes[-2])
            elif isinstance(self.tg_message.media, types.MessageMediaDocument):
                await self.file_download(client, self.tg_message.document, self.tg_message.document.size)
        except Exception as ex:
            logging.error(f"Message {self.message.id} media download failed.")
            logging.exception(ex)
        else:
            logging.info(f"Message {self.message.id} media download success.")
        
    def run(self):
        asyncio.run(self.async_run())