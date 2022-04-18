import os, multiprocessing, setproctitle, asyncio, logging, typing, telethon
import entities, exceptions

if typing.TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.events.chataction import ChatAction

class ChatMediaProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat'):
        multiprocessing.Process.__init__(self, name=f'ChatMediaProcess-{chat.id}', daemon=True)

        setproctitle.setproctitle(self.name)

        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    async def handle_media(self, client: 'TelegramClient', photo: 'telethon.types.TypePhoto'):
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

    async def async_run(self):
        for chat_phone in self.chat.phones:
            chat_phone: 'entities.TypeChatPhone'

            try:
                client = await chat_phone.phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.critical(f"Phone {chat_phone.id} client not available. Exception: {ex}")

                self.chat.phones.remove(chat_phone)
                
                continue

            async def handle_event(event: 'ChatAction.Event'):
                if event.new_photo:
                    await self.handle_media(client, event.photo)

            client.add_event_handler(handle_event, telethon.events.chataction.ChatAction(chats=self.chat.internalId))
            
            while True:
                try:
                    async for photo in client.iter_profile_photos(entity=self.chat.internalId):
                        photo: 'telethon.types.TypePhoto'

                        await self.handle_media(client, photo)
                    else:
                        logging.info(f"Chat \'{self.chat.id}\' participants download success.")
                except telethon.errors.FloodWaitError as ex:
                    logging.error(f"Telegram chat media request of chat {self.chat.id} must wait {ex.seconds} seconds.")

                    await asyncio.wait(ex.seconds)
                except telethon.errors.RPCError as ex:
                    logging.error(f"Can\'t get chat {self.chat.id} using phone {chat_phone.id}. Exception {ex}")
                    
                    break
        else:
            logging.error(f"Can't get chat {self.chat.id} medias.")

    def run(self):
        asyncio.run(self.async_run())
