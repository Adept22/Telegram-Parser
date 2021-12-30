import os
import threading
import asyncio
import logging

from utils.bcolors import bcolors
from telethon import sync, errors
from processors.ApiProcessor import ApiProcessor

class SendCodeThread(threading.Thread):
    def __init__(self, phone):
        threading.Thread.__init__(self)
        
        self.phone = phone
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def async_run(self):
        client = await self.phone.new_client(loop=self.loop)
        
        if client == None:
            return
        
        try:
            print(f"SendCodeThread: Try to send code for {self.id}.", flush=True)
            logging.debug(f"SendCodeThread: Try to send code for {self.id}.")
            
            sent = await client.send_code_request(phone=self.number)
            print(f"SendCodeThread: code sended for {self.id}.", flush=True)
            logging.debug(f"SendCodeThread: code sended for {self.id}.")
            
            ApiProcessor().set('phone', { 'id': self.id, 'isVerified': False, 'code': None, 'codeHash': sent.phone_code_hash })
        except errors.rpcerrorlist.FloodWaitError as ex:
            print(f"{bcolors.WARNING}SendCodeThread: flood exception for {self.id}. Sleep {ex.seconds}.{bcolors.ENDC}", flush=True)
            logging.error(f"SendCodeThread: flood exception for {self.id}. Sleep {ex.seconds}.")
            
            await asyncio.sleep(ex.seconds)
            
            await self.async_run()
        except Exception as ex:
            print(f"{bcolors.FAIL}SendCodeThread: unable to sent code for {self.id}. Exception: {ex}.{bcolors.ENDC}", flush=True)
            logging.error(f"SendCodeThread: unable to sent code for {self.id}. Exception: {ex}.")
            
            # TODO: Открыть после всех тестов
            # ApiProcessor().set('phone', { 'id': self.id, 'isBanned': True, 'code': None, 'codeHash': None })  

    def run(self):
        asyncio.run(self.async_run())
