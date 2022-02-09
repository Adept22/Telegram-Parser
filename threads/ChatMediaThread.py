import os
import re
import threading
import asyncio
import logging
import random

from telethon import types

from processors.ApiProcessor import ApiProcessor

class ChatMediaThread(threading.Thread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'ChatMediaThread-{chat.id}')
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def get_profile_media(self, client):
        photos = await client.get_profile_photos(
            entity = types.PeerChannel(channel_id=self.chat.internal_id)
        )

        for photo in photos:
            saved_photo = { 'internalId': photo.id }

            saved_photos = ApiProcessor().get('chat-media', saved_photo)

            if len(saved_photos) > 0:
                saved_photo = saved_photos[0]

                if os.path.exists(saved_photo['path']):
                    logging.debug(f'Chat {self.chat.id}. Member-media {saved_photo["id"]} exist. Continue.')
                
                    await asyncio.sleep(1)
                    continue

            try:
                path_folder = f'./uploads/chat-media/{self.chat.id}'

                path_to_file = await client.download_media(
                    message=photo,
                    file=f'{path_folder}/{photo.id}',
                    thumb=photo.sizes[-2]
                )

                if path_to_file != None:
                    new_photo = { 
                        'chat': {"id": self.chat.internal_id}, 
                        'internalId': photo.id,
                        'createdAt': photo.date.isoformat(),
                        'path': f'{path_folder}/{re.split("/", path_to_file)[-1]}'
                    }

                    if 'id' in saved_photo:
                        new_photo['id'] = saved_photo['id']
                        
                    ApiProcessor().set('chat-media', new_photo)

            except Exception as ex:
                logging.error(f"Can\'t save chat {self.chat.id} media. Exception: {ex}.")
            else:
                logging.info(f"Sucessfuly saved chat {self.chat.id} media!")

    async def async_run(self):
        for phone in self.chat.phones:
            try:
                client = await phone.new_client(loop=self.loop)

                await self.get_profile_media(client)
            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}. Exception: {ex}.")
            
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                break
        else:
            logging.error(f"Can\'t get chat {self.chat.id} messages.")

            ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
            
            raise Exception(f'Chat {self.chat.id} messages download failed. Exit code 1.')
    def run(self):
        asyncio.run(self.async_run())
