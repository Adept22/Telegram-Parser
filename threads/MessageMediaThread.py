import threading, asyncio, logging, telethon
import entities, exceptions

class MessageMediaThread(threading.Thread):
    def __init__(self, phone: 'entities.TypePhone', message: 'entities.TypeMessage', tg_message: 'telethon.types.TypeMessage'):
        threading.Thread.__init__(self, name=f"MessageMediaThread-{message.id}", daemon=True)
        
        self.phone = phone
        self.message = message
        self.tg_message: 'telethon.types.TypeMessage' = tg_message

        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
    
    async def async_run(self):
        logging.debug(f"Try to save message '{self.message.id}' media.")

        try:
            client = await self.phone.new_client(loop=self.loop)
        except exceptions.ClientNotAvailableError as ex:
            logging.critical(f"Phone {self.phone.id} client not available.")
            
            return

        if isinstance(self.tg_message.media, telethon.types.MessageMediaPhoto):
            entity = self.tg_message.photo
            size = entity.sizes[-2].size
            date = entity.date.isoformat()
            entity = telethon.types.InputPhotoFileLocation(
                id=entity.id,
                access_hash=entity.access_hash,
                file_reference=entity.file_reference,
                thumb_size=size.type
            )
        elif isinstance(self.tg_message.media, telethon.types.MessageMediaDocument):
            entity = self.tg_message.document
            size = entity.size
            date = entity.date.isoformat()
            entity = telethon.types.InputDocumentFileLocation(
                id=entity.id,
                access_hash=entity.access_hash,
                file_reference=entity.file_reference,
                thumb_size=''
            )
        else:
            return

        # TODO:
        # elif isinstance(self.tg_message.media, telethon.types.MessageMediaPoll):
        #     pass
        # elif isinstance(self.tg_message.media, telethon.types.MessageMediaVenue):
        #     pass
        # elif isinstance(self.tg_message.media, telethon.types.MessageMediaContact):
        #     pass
        
        media = entities.MessageMedia(internalId=entity.id, message=self.message, date=date)
        
        try:
            media.save()
        except exceptions.RequestException as ex:
            logging.error(f"Can\'t save message {self.message.id} media. Exception: {ex}.")
        else:
            logging.info(f"Sucessfuly saved message {self.message.id} media.")

            try:
                await media.upload(client, entity, size)
            except exceptions.RequestException as ex:
                logging.error(f"Can\'t upload message {self.message.id} media. Exception: {ex}.")
            else:
                logging.info(f"Sucessfuly uploaded message {self.message.id} media.")

    def run(self):
        asyncio.run(self.async_run())