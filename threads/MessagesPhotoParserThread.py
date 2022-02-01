import os
from re import split
import threading
import asyncio
import logging
import random
from utils import formated_date

from telethon import types

from processors.ApiProcessor import ApiProcessor

class MessagesPhotoParserThread(threading.Thread):
    def __init__(self, chat):
        threading.Thread.__init__(self, name=f'ChatMessagesPhotoThread-{chat.id}')
        
        self.chat = chat
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def get_photo_messages(self, client):
        photo_messages = await client.get_messages(
            entity = types.PeerChannel(channel_id=self.chat.internal_id),
            limit = int(os.environ['MESSAGES_LIMIT']),
            filter = types.InputMessagesFilterPhotos
        )

        for message in photo_messages:
            photo = message.photo
            saved_photo = { 'internalId': photo.id }

            saved_photos = ApiProcessor().get('message-media', saved_photo)

            if len(saved_photos) > 0:
                saved_photo = saved_photos[0]

                if os.path.exists(saved_photo['path']):
                    logging.debug(f'Chat {self.chat.id}. Message-photo {saved_photo["id"]} exist. Continue.')
                
                    await asyncio.sleep(1)
                    continue

            try:
                path_folder = f'{os.environ["UPLOAD_PATH"]}/message-media/{self.chat.id}'

                path_to_file = await client.download_media(
                    message=photo,
                    file=f'{path_folder}/{photo.id}',
                    thumb=photo.sizes[-1]
                )

                if path_to_file != None:
                    new_photo = { 
                        'chat': {"id": self.chat.id}, 
                        'internalId': photo.id,
                        # 'createdAt': photo.date.isoformat(),
                        'createdAt': formated_date(photo.date),
                        'path': f'{path_folder}/{split("/", path_to_file)[-1]}'
                    }

                    if 'id' in saved_photo:
                        new_photo['id'] = saved_photo['id']
                        
                    ApiProcessor().set('message-media', new_photo)

            except Exception as ex:
                logging.error(f"Can\'t save message {photo.id} photo. Exception: {ex}.")
            else:
                logging.info(f"Sucessfuly saved message {photo.id} photo!")

    async def async_run(self):
        for phone in self.chat.phones:
            try:
                client = await phone.new_client(loop=self.loop)

                await self.get_photo_messages(client)
            except Exception as ex:
                logging.error(f"Can\'t get chat {self.chat.id} using phone {phone.id}. Exception: {ex}.")
            
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                break
        else:
            logging.error(f"Can\'t get chat {self.chat.id} photo messages.")

            # ApiProcessor().set('chat', { 'id': self.chat.id, 'isAvailable': False })
            
            raise Exception(f'Chat {self.chat.id} photo messages download failed. Exit code 1.')
    def run(self):
        asyncio.run(self.async_run())