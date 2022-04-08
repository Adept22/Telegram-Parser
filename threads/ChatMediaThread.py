import os
import threading
import asyncio
import logging
import random
import requests

from telethon import types
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError
from models.ChatMediaEntity import ChatMedia

from processors.ApiProcessor import ApiProcessor
from threads.KillableThread import KillableThread

class ChatMediaThread(KillableThread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'ChatMediaThread-{chat.id}')
        self.daemon = True

        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)

    async def get_entity(self, client):
        try:
            return await client.get_entity(entity=types.PeerChannel(channel_id=self.chat.internal_id))
        except ValueError:
            return await client.get_entity(entity=types.PeerChat(chat_id=self.chat.internal_id))
        
    async def async_run(self):
        for phone in self.chat.phones:
            try:
                client = await phone.new_client(loop=self.loop)

                entity = await self.get_entity(client)
                
                async for photo in client.iter_profile_photos(entity=entity):
                    try:
                        media = ChatMedia(internalId=photo.id, chat=self.chat, date=photo.date.isoformat())
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
        self.chat.init_event.wait()

        asyncio.run(self.async_run())
