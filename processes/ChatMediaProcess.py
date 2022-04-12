import multiprocessing, asyncio, logging, random, telethon
import entity

class ChatMediaProcess(multiprocessing.Process):
    def __init__(self, chat):
        multiprocessing.Process.__init__(self, name=f'ChatMediaProcess-{chat.id}', daemon=True)

        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    async def get_profile(self, client):
        try:
            return await client.get_entity(entity=telethon.types.PeerChannel(channel_id=self.chat.internal_id))
        except ValueError:
            return await client.get_entity(entity=telethon.types.PeerChat(chat_id=self.chat.internal_id))
        
    async def async_run(self):
        for phone in self.chat.phones:
            try:
                client = await phone.new_client(loop=self.loop)

                profile = await self.get_profile(client)
                
                async for photo in client.iter_profile_photos(entity=profile):
                    try:
                        media = entity.ChatMedia(internalId=photo.id, chat=self.chat, date=photo.date.isoformat())
                        media.save()
                    except Exception as ex:
                        logging.error(f"Can\'t save chat {self.chat.id} media. Exception: {ex}.")
                        logging.exception(ex)
                    else:
                        logging.info(f"Sucessfuly saved chat {self.chat.id} media.")

                        try:
                            await media.upload(client, photo, photo.sizes[-2])
                        except Exception as ex:
                            logging.error(f"Can\'t upload chat {self.chat.id} media.")
                            logging.exception(ex)
                        else:
                            logging.info(f"Sucessfuly uploaded chat {self.chat.id} media.")
            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}.")
                logging.exception(ex)
            
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                break
        else:
            logging.error(f"Can't get chat {self.chat.id} messages.")

    def run(self):
        asyncio.run(self.async_run())
