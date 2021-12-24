import os
import threading
import asyncio
import logging

from utils.bcolors import bcolors
from telethon import sync, errors
from processors.ApiProcessor import ApiProcessor

class SendCodeThread(threading.Thread):
    def __init__(self, id, number, loop):
        threading.Thread.__init__(self)
        
        self.id = id
        self.number = number
        self.loop = loop
        
        asyncio.set_event_loop(self.loop)
        
        self.client = sync.TelegramClient(
            session=f"sessions/{self.number}.session", 
            api_id=os.environ['TELEGRAM_API_ID'],
            api_hash=os.environ['TELEGRAM_API_HASH'],
            loop=self.loop
        )
        
    async def async_run(self):
        try:
            if not self.client.is_connected():
                await self.client.connect()
            
            print(f"SendCodeThread: Try to send code for {self.id}.", flush=True)
            logging.debug(f"SendCodeThread: Try to send code for {self.id}.")
            
            sent = await self.client.send_code_request(phone=self.number)
        except errors.rpcerrorlist.FloodWaitError as ex:
            print(f"{bcolors.WARNING}SendCodeThread: flood exception for {self.id}. Sleep {ex.seconds}.{bcolors.ENDC}", flush=True)
            logging.error(f"SendCodeThread: flood exception for {self.id}. Sleep {ex.seconds}.")
            
            await asyncio.sleep(ex.seconds)
            
            await self.async_run()
        except Exception as ex:
            print(f"{bcolors.FAIL}SendCodeThread: unable to sent code for {self.id}. Exception: {ex}.{bcolors.ENDC}", flush=True)
            logging.error(f"SendCodeThread: unable to sent code for {self.id}. Exception: {ex}.")
        else:
            print(f"SendCodeThread: code sended for {self.id}.", flush=True)
            logging.debug(f"SendCodeThread: code sended for {self.id}.")
            
            ApiProcessor().set('phone', { 'id': self.id, 'isVerified': False, 'code': None, 'codeHash': sent.phone_code_hash })

    def run(self):
        asyncio.run(self.async_run())
