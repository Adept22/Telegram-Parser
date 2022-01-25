import os
import threading
import asyncio
import logging

from telethon import sync, errors, sessions
from processors.ApiProcessor import ApiProcessor

class AuthorizationThread(threading.Thread):
    def __init__(self, phone):
        threading.Thread.__init__(self, name=f'AuthorizationThread-{phone.id}')
        
        self.retry = 0
        self.phone = phone
        
        self.loop = asyncio.new_event_loop()
        
        self.client = sync.TelegramClient(
            session=sessions.StringSession(self.phone.session), 
            api_id=os.environ['TELEGRAM_API_ID'],
            api_hash=os.environ['TELEGRAM_API_HASH'],
            loop=self.loop
        )
        
        asyncio.set_event_loop(self.loop)
        
    async def send_code(self):
        try:
            logging.debug(f"Try to send code for {self.phone.id}.")
            
            sent = await self.client.send_code_request(phone=self.phone.number)
            
            logging.debug(f"Code sended for {self.phone.id}.")
            
            self.phone.is_verified = False
            self.phone.code = None
            self.phone.code_hash = sent.phone_code_hash
        except errors.rpcerrorlist.FloodWaitError as ex:
            logging.error(f"Flood exception for phone {self.phone.id}. Sleep {ex.seconds}.")
            
            await asyncio.sleep(ex.seconds)
            
            await self.send_code()

    async def async_run(self):
        if not self.client.is_connected():
            await self.client.connect()
            
        while True:
            if not await self.client.is_user_authorized():
                if self.phone.code != None and self.phone.code_hash != None:
                    logging.debug(f"Phone {self.phone.id} automatic try to sing in with code {self.phone.code}.")
        
                    try:
                        await self.client.sign_in(
                            phone=self.phone.number, 
                            code=self.phone.code, 
                            phone_code_hash=self.phone.code_hash
                        )
                    except Exception as ex:
                        logging.error(f"Cannot authentificate phone {self.phone.id} with code {self.phone.code}. Exception: {ex}.")
                        
                        logging.warning(f"Sleep 1 minute before sending new code for phone {self.phone.id}.")

                        await asyncio.sleep(60)
                        
                        self.phone.is_verified = False
                        self.phone.code = None
                        self.phone.code_hash = None
                        
                        self.phone.save()
                    else:
                        self.phone.session = self.client.session.save()
                        self.phone.is_verified = True
                        self.phone.code = None
                        self.phone.code_hash = None
                        
                        self.phone.save()
                        
                        break
                elif self.phone.code_hash == None:
                    try:
                        await self.send_code()
                    except Exception as ex:
                        logging.error(f"Unable to sent code for {self.phone.id}. Exception: {ex}.")
                        
                        self.phone.authorization_thread = None
                        self.phone.session = self.client.session.save()
                        self.phone.is_banned = True
                        self.phone.is_verified = False
                        self.phone.code = None
                        self.phone.code_hash = None
                        
                        self.phone.save()
                else:
                    await asyncio.sleep(10)
            else:
                logging.debug(f"Phone {self.phone.id} actually authorized.")
                
                self.phone.authorization_thread = None
                
                if self.phone.session != self.client.session.save():
                    self.phone.session = self.client.session.save()
                    
                    self.phone.is_banned = False
                    self.phone.is_verified = True
                    self.phone.code = None
                    self.phone.code_hash = None
                            
                    self.phone.save()
                
                break
                
    def run(self):
        asyncio.run(self.async_run())
