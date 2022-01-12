from os import name
from re import split
import threading
import asyncio
import logging
import random

from telethon import errors, types

from processors.ApiProcessor import ApiProcessor
from utils import bcolors
from errors.ChatNotAvailableError import ChatNotAvailableError
from errors.ClientNotAvailableError import ClientNotAvailableError

class MessageMediaThread(threading.Thread):
    def __init__(self, chat, phone, message, tg_message):
        threading.Thread.__init__(self)
        
        self.chat = chat
        self.phone = phone
        self.message = message
        self.tg_message = tg_message
        
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
            
    async def async_run(self):
        try:
            print(f'Try to save message \'{self.message["id"]}\' media.')
            logging.debug(f'Try to save message \'{self.message["id"]}\' media.')

            client = await self.phone.new_client(loop=self.loop)
            
            if isinstance(self.tg_message.media, types.MessageMediaPoll):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaVenue):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaContact):
                pass
            elif isinstance(self.tg_message.media, types.MessageMediaPhoto):
                def progress_callback(current, total):
                    print(f'Message \'{self.message["id"]}\' media downloaded {current} out of {total} bytes: {current / total:.2%}')
                    logging.debug(f'Message \'{self.message["id"]}\' media downloaded {current} out of {total} bytes: {current / total:.2%}')
                
                path = await client.download_media(
                    message=self.tg_message,
                    file=f'../../uploads/{self.chat.id}/{self.message["id"]}/{self.tg_message.id}',
                    progress_callback=progress_callback
                )

                if path != None:
                    media = ApiProcessor().set('message-media', { 
                        'message': { "id": self.message["id"] }, 
                        'path': f'/uploads/{self.chat.id}/{self.message["id"]}/{split("/", path)[-1]}', 
                    })
            elif isinstance(self.tg_message.media, types.MessageMediaDocument):
                def progress_callback(current, total):
                    print(f'Message \'{self.message["id"]}\' media downloaded {current} out of {total} bytes: {current / total:.2%}')
                    logging.debug(f'Message \'{self.message["id"]}\' media downloaded {current} out of {total} bytes: {current / total:.2%}')
                
                path = await self.tg_message.download_media(
                    message=self.tg_message,
                    file=f'../../uploads/{self.chat.id}/{self.message["id"]}/{self.tg_message.id}',
                    progress_callback=progress_callback
                )

                if path != None:
                    media = ApiProcessor().set('message-media', { 
                        'message': { "id": self.message["id"] }, 
                        'path': f'/uploads/{self.chat.id}/{self.message["id"]}/{split("/", path)[-1]}'
                    })
        except Exception as ex:
            print(f"{bcolors.FAIL}Can\'t save message {self.message['id']} media. Exception: {ex}.{bcolors.ENDC}")
            logging.error(f"Can\'t save message {self.message['id']} media. Exception: {ex}.")

    def run(self):
        asyncio.run(self.async_run())