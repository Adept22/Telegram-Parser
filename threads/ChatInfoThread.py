import asyncio, logging, typing, telethon
import entities, exceptions
import services

if typing.TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.events.chataction import ChatAction

async def _chat_info_thread(chat: 'entities.TypeChat'):
    def handle_title(new_title: 'str'):
        chat.title = new_title

        try:
            chat.save()
        except exceptions.RequestException:
            return

    async def handle_media(client: 'TelegramClient', photo: 'telethon.types.TypePhoto'):
        media = entities.ChatMedia(internalId=photo.id, chat=chat, date=photo.date.isoformat())

        try:
            media.save()
        except exceptions.RequestException as ex:
            logging.error(f"Can't save chat media. Exception: {ex}.")
        else:
            logging.info(f"Chat media saved.")

            size = next(((size.type, size.size) for size in photo.sizes if isinstance(size, telethon.types.PhotoSize)), ('', None))
            tg_media = telethon.types.InputPhotoFileLocation(photo.id, photo.access_hash, photo.file_reference, size[0])
            extension = telethon.utils.get_extension(photo)
            
            try:
                await media.upload(client, tg_media, size[1], extension)
            except exceptions.RequestException as ex:
                logging.error(f"Can't upload chat media. Exception: {ex}.")
            else:
                logging.info(f"Chat {chat.id} media uploaded.")

    for chat_phone in chat.phones:
        chat_phone: 'entities.TypeChatPhone'

        async with services.ChatPhoneClient(chat_phone) as client:
            async def handle_event(event: 'ChatAction.Event'):
                if event.new_photo:
                    await handle_media(client, event.photo)

                if event.new_title:
                    handle_title(event.new_title)

            client.add_event_handler(handle_event, telethon.events.chataction.ChatAction(chats=chat.internalId))
            
            while True:
                try:
                    async for photo in client.iter_profile_photos(entity=chat.internalId):
                        photo: 'telethon.types.TypePhoto'

                        await handle_media(client, photo)
                except telethon.errors.FloodWaitError as ex:
                    logging.warning(f"Chat media request must wait {ex.seconds} seconds.")

                    await asyncio.sleep(ex.seconds)

                    continue
                except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                    logging.critical(f"Can't get chat using phone {chat_phone.id}. Exception {ex}")

                    chat.isAvailable = False
                    chat.save()
                else:
                    logging.info(f"Chat medias download success.")
                    
                return
    else:
        logging.error(f"Can't get chat medias.")

def chat_info_thread(chat: 'entities.TypeChat'):
    asyncio.run(_chat_info_thread(chat))