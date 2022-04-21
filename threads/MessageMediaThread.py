import asyncio, logging, telethon
import entities, exceptions
import services

async def _message_media_thread(chat_phone: 'entities.TypeChatPhone', message: 'entities.TypeMessage', tg_message: 'telethon.types.TypeMessage'):
    logging.debug(f"Try to save message '{message.id}' media.")

    async with services.ChatPhoneClient(chat_phone) as client:
        if isinstance(tg_message.media, telethon.types.MessageMediaPhoto):
            entity = tg_message.photo
            _size = next(((size.type, size.size) for size in entity.sizes if isinstance(size, telethon.types.PhotoSize)), ('', None))
            size = _size[1]
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
            logging.info(f"Sucessfuly saved message {message.id} media.")

            try:
                await media.upload(client, entity, size)
            except exceptions.RequestException as ex:
                logging.error(f"Can\'t upload message {message.id} media. Exception: {ex}.")
            else:
                logging.info(f"Sucessfuly uploaded message {message.id} media.")

def message_media_thread(chat_phone: 'entities.TypeChatPhone', message: 'entities.TypeMessage', tg_message: 'telethon.types.TypeMessage'):
    asyncio.run(_message_media_thread(chat_phone, message, tg_message))
