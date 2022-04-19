import os, threading, asyncio, logging, typing, telethon
import entities, exceptions

if typing.TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.events.chataction import ChatAction

class ChatInfoThread(threading.Thread):
    def __init__(self, chat: 'entities.TypeChat'):
        threading.Thread.__init__(self, name=f'ChatInfoThread-{chat.id}', daemon=True)

        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    def handle_title(self, new_title: 'str'):
        self.chat.title = new_title

        try:
            self.chat.save()
        except exceptions.RequestException:
            return

    async def handle_media(self, client: 'TelegramClient', photo: 'telethon.types.TypePhoto'):
        media = entities.ChatMedia(internalId=photo.id, chat=self.chat, date=photo.date.isoformat())

        try:
            media.save()
        except exceptions.RequestException as ex:
            logging.error(f"Can't save chat {self.chat.id} media. Exception: {ex}.")
        else:
            logging.info(f"Successfuly saved chat {self.chat.id} media.")

            size = next(((size.type, size.size) for size in photo.sizes if isinstance(size, telethon.types.PhotoSize)), ('', None))

            try:
                await media.upload(client, telethon.types.InputPhotoFileLocation(photo.id, photo.access_hash, photo.file_reference, size[0]), size[1])
            except exceptions.RequestException as ex:
                logging.error(f"Can't upload chat {self.chat.id} media. Exception: {ex}.")
            else:
                logging.info(f"Successfuly uploaded chat {self.chat.id} media.")

    async def async_run(self):
        for chat_phone in self.chat.phones:
            chat_phone: 'entities.TypeChatPhone'

            try:
                client = await chat_phone.phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.critical(f"Phone {chat_phone.id} client not available. Exception: {ex}")

                chat_phone.isUsing = False
                chat_phone.save()
                
                self.chat.phones.remove(chat_phone)
                
                continue

            async def handle_event(event: 'ChatAction.Event'):
                if event.new_photo:
                    await self.handle_media(client, event.photo)

                if event.new_title:
                    self.handle_title(event.new_title)

            client.add_event_handler(handle_event, telethon.events.chataction.ChatAction(chats=self.chat.internalId))
            
            while True:
                try:
                    async for photo in client.iter_profile_photos(entity=self.chat.internalId):
                        photo: 'telethon.types.TypePhoto'

                        await self.handle_media(client, photo)
                    else:
                        logging.info(f"Chat {self.chat.id} medias download success.")
                except telethon.errors.FloodWaitError as ex:
                    logging.error(f"Telegram chat media request of chat {self.chat.id} must wait {ex.seconds} seconds.")

                    await asyncio.sleep(ex.seconds)
                except (KeyError, ValueError, telethon.errors.RPCError) as ex:
                    logging.error(f"Can't get chat {self.chat.id} using phone {chat_phone.id}. Exception {ex}")
                    
                    break
        else:
            logging.error(f"Can't get chat {self.chat.id} medias.")

    def run(self):
        asyncio.run(self.async_run())
