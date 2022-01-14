import threading
import asyncio
import logging
from utils import bcolors

from telethon import types

from processors.ApiProcessor import ApiProcessor

class MessageMediaThread(threading.Thread):
    def __init__(self, chat, message, tg_message):
        threading.Thread.__init__(self, name=f'MessageMediaThread-{message["id"]}')
        
        self.chat = chat
        self.message = message
        self.tg_message = tg_message
        
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
            
    async def async_run(self):
        try:
            logging.debug(f'Try to save message \'{self.message["id"]}\' media.')
            
            if isinstance(self.tg_message.media, types.MessageMediaPoll):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaVenue):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaContact):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaDocument):
                def progress_callback(current, total):
                    logging.debug(f'Message \'{self.message["id"]}\' media downloaded {current} out of {total} bytes: {current / total:.2%}')
                
                path = await self.tg_message.download_media(
                    file=f'/uploads/{self.chat.id}/{self.message["id"]}/',
                    progress_callback=progress_callback
                )

                if path != None:
                    media = ApiProcessor().set('message-media', { 
                        'message': { "id": self.message["id"] }, 
                        'path': path, 
                    })
        except Exception as ex:
            logging.error(f"Can\'t save chat {self.chat.id} message. Exception: {ex}.")

    def run(self):
        asyncio.run(self.async_run())