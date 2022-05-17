import asyncio, logging, telethon
import entities, exceptions, services

async def _message_media_process(chat_phone: 'entities.TypeChatPhone', message: 'entities.TypeMessage', tg_message: 'telethon.types.TypeMessage'):
    async with services.ChatPhoneClient(chat_phone) as client:
        if isinstance(tg_message.media, telethon.types.MessageMediaPhoto):
            entity = tg_message.photo
            _size = next(((size.type, size.size) for size in entity.sizes if isinstance(size, telethon.types.PhotoSize)), ('', None))
            size = _size[1]
            extension = telethon.utils.get_extension(entity)
            date = entity.date.isoformat()
            entity = telethon.types.InputPhotoFileLocation(
                id=entity.id,
                access_hash=entity.access_hash,
                file_reference=entity.file_reference,
                thumb_size=_size[0]
            )
        elif isinstance(tg_message.media, telethon.types.MessageMediaDocument):
            entity = tg_message.document
            size = entity.size
            extension = telethon.utils.get_extension(entity)
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
        # elif isinstance(tg_message.media, telethon.types.MessageMediaPoll):
        #     pass
        # elif isinstance(tg_message.media, telethon.types.MessageMediaVenue):
        #     pass
        # elif isinstance(tg_message.media, telethon.types.MessageMediaContact):
        #     pass
        
        media = entities.MessageMedia(internalId=entity.id, message=message, date=date)
        
        try:
            media.save()
        except exceptions.RequestException as ex:
            logging.error(f"Can\'t save message {message.id} media. Exception: {ex}.")
        else:
            logging.info(f"Successfully saved message {message.id} media.")

            try:
                await media.upload(client, entity, size, extension)
            except exceptions.RequestException as ex:
                logging.error(f"Can\'t upload message {message.id} media. Exception: {ex}.")
            else:
                logging.info(f"Successfully uploaded message {message.id} media.")

def message_media_process(chat_phone: 'entities.TypeChatPhone', message: 'entities.TypeMessage', tg_message: 'telethon.types.TypeMessage'):
    asyncio.set_event_loop(asyncio.new_event_loop())
    
    asyncio.run(_message_media_process(chat_phone, message, tg_message))
