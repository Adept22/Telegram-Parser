import os
import threading
import asyncio
import logging
import random

from telethon import types

from processors.ApiProcessor import ApiProcessor
from threads.KillableThread import KillableThread

class ChatMediaThread(KillableThread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'ChatMediaThread-{chat.id}')
        self.daemon = True
        
        self.media_path = f"./downloads/chat/{chat.id}/avatars"

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
                    new_media = { 'internalId': photo.id }

                    medias = ApiProcessor().get('telegram/chat-media', new_media)

                    if len(medias) > 0:
                        new_media = medias[0]
                                
                        if 'path' in new_media and new_media['path'] != None:
                            logging.debug(f"Member {self.chat.id} media {new_media['id']} exist on server. Continue.")

                            await asyncio.sleep(1)

                            continue

                    def progress_callback(current, total):
                        logging.debug(f"Chat '{self.chat.id}' media downloaded {current} out of {total} bytes: {current / total:.2%}")

                    try:
                        path = await client.download_media(
                            message=photo,
                            file=f"{self.media_path}/{photo.id}",
                            thumb=photo.sizes[-2],
                            progress_callback=progress_callback
                        )

                        if path != None:
                            new_media = { 
                                **new_media, 
                                'chat': {"id": self.chat.id}, 
                                'internalId': photo.id, 
                                'createdAt': photo.date.isoformat()
                            }
                                
                            new_media = ApiProcessor().set('telegram/chat-media', new_media)

                            try:
                                ApiProcessor().upload('telegram/chat-media', new_media, path)
                            except Exception as ex:
                                logging.error(f"Can\'t upload chat {self.chat.id} media. Exception: {ex}.")
                            else:
                                logging.info(f"Sucessfuly uploaded chat {self.chat.id} media.")

                                try:
                                    os.remove(path)
                                except:
                                    pass
                    except Exception as ex:
                        logging.error(f"Can\'t save chat {self.chat.id} media. Exception: {ex}.")
                    else:
                        logging.info(f"Sucessfuly saved chat {self.chat.id} media!")
            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}. Exception: {ex}.")
            
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                break
        else:
            logging.error(f"Can't get chat {self.chat.id} messages.")

    def run(self):
        self.chat.init_event.wait()

        asyncio.run(self.async_run())
