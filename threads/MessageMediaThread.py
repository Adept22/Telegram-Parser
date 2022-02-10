import os
import threading
import asyncio
import logging
from telethon import types

from processors.ApiProcessor import ApiProcessor

class MessageMediaThread(threading.Thread):
    def __init__(self, phone, message, tg_message):
        threading.Thread.__init__(self, name=f"MessageMediaThread-{message['id']}")

        self.media_path = f"./uploads/chat/{message['chat']['id']}/messages"
        
        self.phone = phone
        self.message = message
        self.tg_message = tg_message

        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
    
    async def file_download(self, client):
        new_media = { 'internalId': self.tg_message.media.id }

        medias = ApiProcessor().get('message-media', new_media)

        if len(medias) > 0:
            new_media = medias[0]

            if os.path.exists(new_media['path']):
                logging.debug(f"Message media {new_media['id']} exist. Continue.")
            
                await asyncio.sleep(1)

                return

        try:
            def progress_callback(current, total):
                logging.debug(f"Message '{self.message['id']}' media downloaded {current} out of {total} bytes: {current / total:.2%}")

            path = await client.download_media(
                message=self.tg_message,
                file=f"{self.media_path}/{self.message['id']}",
                thumb=self.tg_message.media.sizes[-2],
                progress_callback=progress_callback
            )

            if path != None:
                new_media = {
                    **new_media,
                    'message': {"id": self.message['id']}, 
                    'createdAt': self.tg_message.date.isoformat(), 
                    'path': path[2:]
                }

                ApiProcessor().set('message-media', new_media)
        except Exception as ex:
            logging.error(f"Can't save chat {self.chat.id} media. Exception: {ex}.")
        else:
            logging.info(f"Sucessfuly saved chat {self.chat.id} media!")

    async def async_run(self):
        try:
            logging.debug(f"Try to save message '{self.message['id']}' media.")

            client = await self.phone.new_client(loop=self.loop)
            
            if isinstance(self.tg_message.media, types.MessageMediaPoll):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaVenue):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaContact):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaPhoto):
                await self.file_download(client)
            elif isinstance(self.tg_message.media, types.MessageMediaDocument):
                await self.file_download(client)
        except Exception as ex:
            logging.error(f"Message {self.message['id']} media download failed. Exit code 1. Exception: {ex}.")
        else:
            logging.info(f"Message {self.message['id']} media download success. Exit code 0.")
        
    def run(self):
        asyncio.run(self.async_run())