import multiprocessing, asyncio, logging, random, telethon
import entities, exceptions

class ChatMediaProcess(multiprocessing.Process):
    def __init__(self, chat: 'entities.TypeChat'):
        multiprocessing.Process.__init__(self, name=f'ChatMediaProcess-{chat.id}', daemon=True)

        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    async def async_run(self):
        for phone in self.chat.phones:
            try:
                client = await phone.new_client(loop=self.loop)
            except exceptions.ClientNotAvailableError as ex:
                logging.error(f"Phone {phone.id} client not available.")
                logging.exception(ex)

                self.chat.remove_phone(phone)
                self.chat.save()
                
                continue

            try:
                tg_chat = await self.chat.get_tg_entity(client)
            except exceptions.ChatNotAvailableError as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}.")
                logging.exception(ex)

                self.chat.isAvailable = False
                self.chat.save()

                break
                
            try:
                async for photo in client.iter_profile_photos(entity=tg_chat):
                    photo: 'telethon.types.TypePhoto'

                    media = entities.ChatMedia(internalId=photo.id, chat=self.chat, date=photo.date.isoformat())

                    try:
                        media.save()
                    except exceptions.RequestException as ex:
                        logging.error(f"Can\'t save chat {self.chat.id} media. Exception: {ex}.")
                        logging.exception(ex)
                    else:
                        logging.info(f"Sucessfuly saved chat {self.chat.id} media.")

                        try:
                            await media.upload(client, photo, photo.sizes[-2])
                        except exceptions.RequestException as ex:
                            logging.error(f"Can\'t upload chat {self.chat.id} media.")
                            logging.exception(ex)
                        else:
                            logging.info(f"Sucessfuly uploaded chat {self.chat.id} media.")
            except (
                telethon.errors.UserIdInvalidError, 
                telethon.errors.ChatAdminRequiredError, 
                telethon.errors.InputUserDeactivatedError, 
                telethon.errors.PeerIdInvalidError, 
                telethon.errors.PeerIdNotSupportedError, 
                telethon.errors.UserIdInvalidError, 
                telethon.errors.ChannelInvalidError, 
                telethon.errors.ChannelPrivateError, 
                telethon.errors.ChannelPublicGroupNaError, 
                telethon.errors.TimeoutError
            ) as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}.")
                logging.exception(ex)
                
                continue
            else:
                break
        else:
            logging.error(f"Can't get chat {self.chat.id} messages.")

    def run(self):
        asyncio.run(self.async_run())
