import os
import threading
import asyncio
import logging

from utils import bcolors
from telethon import sync, errors
from processors.ApiProcessor import ApiProcessor

class AuthorizationThread(threading.Thread):
    def __init__(self, phone):
        threading.Thread.__init__(self)
        
        self.retry = 0
        self.phone = phone
        
        self.loop = asyncio.new_event_loop()
        
        self.client = sync.TelegramClient(
            session=self.phone.session, 
            api_id=os.environ['TELEGRAM_API_ID'],
            api_hash=os.environ['TELEGRAM_API_HASH'],
            loop=self.loop
        )
        
        asyncio.set_event_loop(self.loop)
        
    async def send_code(self):
        try:
            print(f"AuthorizationThread: Try to send code for {self.phone.id}.", flush=True)
            logging.debug(f"AuthorizationThread: Try to send code for {self.phone.id}.")
            
            sent = await self.client.send_code_request(phone=self.phone.number)
            print(f"AuthorizationThread: code sended for {self.phone.id}.", flush=True)
            logging.debug(f"AuthorizationThread: code sended for {self.phone.id}.")
            
            ApiProcessor().set('phone', { 'id': self.phone.id, 'isVerified': False, 'code': None, 'codeHash': sent.phone_code_hash })
        except errors.rpcerrorlist.FloodWaitError as ex:
            print(f"{bcolors.WARNING}AuthorizationThread: flood exception for {self.phone.id}. Sleep {ex.seconds}.{bcolors.ENDC}", flush=True)
            logging.error(f"AuthorizationThread: flood exception for {self.phone.id}. Sleep {ex.seconds}.")
            
            await asyncio.sleep(ex.seconds)
            
            await self.send_code()
        except Exception as ex:
            print(f"{bcolors.FAIL}AuthorizationThread: unable to sent code for {self.phone.id}. Exception: {ex}.{bcolors.ENDC}", flush=True)
            logging.error(f"AuthorizationThread: unable to sent code for {self.phone.id}. Exception: {ex}.")
            
    async def sign_in(self):
        print(f"Phone {self.phone.id} automatic try to sing in with code {self.phone.code}.")
        logging.debug(f"Phone {self.phone.id} automatic try to sing in with code {self.phone.code}.")
        
        try:
            await self.client.sign_in(
                phone=self.phone.number, 
                code=self.phone.code, 
                phone_code_hash=self.phone.code_hash
            )
        except Exception as ex:
            print(f"{bcolors.FAIL}Cannot authentificate phone {self.phone.id} with code {self.phone.code}. Exception: {ex}.{bcolors.ENDC}")
            logging.error(f"Cannot authentificate phone {self.phone.id} with code {self.phone.code}. Exception: {ex}.")
            
            ApiProcessor().set('phone', { 'id': self.phone.id, 'session': None, 'isVerified': False, 'code': None })
        else:
            ApiProcessor().set('phone', { 'id': self.phone.id, 'session': self.client.session.save(), 'isVerified': True, 'code': None, 'codeHash': None })

    async def async_run(self):
        if not self.client.is_connected():
            await self.client.connect()
            
        if not await self.client.is_user_authorized():
            if self.phone.code != None and self.phone.code_hash != None:
                await self.sign_in()
            elif self.phone.code_hash == None: 
                await self.send_code()
            else:
                self.retry += 1
                
                if self.retry <= 50:
                    await asyncio.sleep(10)
                    
                    await self.async_run()
                else:
                    print(f"{bcolors.FAIL}Cannot authentificate phone {self.phone.id}. Code sended code expired.{bcolors.ENDC}")
                    logging.error(f"Cannot authentificate phone {self.phone.id}. Code sended code expired.")
        else:
            print(f"{bcolors.FAIL}Phone {self.phone.id} actually authorized.{bcolors.ENDC}")
            logging.error(f"Phone {self.phone.id} actually authorized.")
                
    def run(self):
        asyncio.run(self.async_run())
        
        self.phone.authorization_thread = None
