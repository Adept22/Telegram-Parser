import asyncio, logging, typing, telethon
import entities, exceptions

if typing.TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.events.chataction import ChatAction

def chat_info_thread(chat: 'entities.TypeChat'):
    asyncio.run(_chat_info_thread(chat))

async def _chat_info_thread(chat: 'entities.TypeChat'):
    loop = asyncio.new_event_loop()
    
    asyncio.set_event_loop(loop)

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
            logging.error(f"Can't save chat {chat.id} media. Exception: {ex}.")
        else:
            logging.info(f"Successfuly saved chat {chat.id} media.")

            size = next(((size.type, size.size) for size in photo.sizes if isinstance(size, telethon.types.PhotoSize)), ('', None))

            try:
                await media.upload(client, telethon.types.InputPhotoFileLocation(photo.id, photo.access_hash, photo.file_reference, size[0]), size[1])
            except exceptions.RequestException as ex:
                logging.error(f"Can't upload chat {chat.id} media. Exception: {ex}.")
            else:
                logging.info(f"Successfuly uploaded chat {chat.id} media.")

    for chat_phone in chat.phones:
        chat_phone: 'entities.TypeChatPhone'

        try:
            client = await chat_phone.phone.new_client(loop=loop)
        except exceptions.ClientNotAvailableError as ex:
            logging.critical(f"Phone {chat_phone.id} client not available. Exception: {ex}")

            chat_phone.isUsing = False
            chat_phone.save()
            
            chat.phones.remove(chat_phone)
            
            continue

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
                else:
                    logging.info(f"Chat {chat.id} medias download success.")
            except telethon.errors.FloodWaitError as ex:
                logging.error(f"Telegram chat media request of chat {chat.id} must wait {ex.seconds} seconds.")

                await asyncio.sleep(ex.seconds)
            except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                logging.error(f"Can't get chat {chat.id} using phone {chat_phone.id}. Exception {ex}")
                
                break
    else:
        logging.error(f"Can't get chat {chat.id} medias.")
