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
        
    async def get_internal_id(self):
        try:
            me = await self.client.get_me()
            
            if me != None:
                return me.id
        except:
            pass
        
        return None
        
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
        new_phone = { "id": self.phone.id }
        
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
                        
                        self.phone.is_verified = False
                        self.phone.code = None
                        self.phone.code_hash = None
                        
                        new_phone['isVerified'] = self.phone.is_verified
                        new_phone['code'] = self.phone.code
                        
                        break
                    else:
                        self.phone.session = self.client.session.save()
                        self.phone.is_verified = True
                        self.phone.code = None
                        self.phone.code_hash = None
                        
                        new_phone['session'] = self.phone.session
                        new_phone['isVerified'] = self.phone.is_verified
                        new_phone['code'] = self.phone.code
                        
                        break
                elif self.phone.code_hash == None:
                    try:
                        await self.send_code()
                    except Exception as ex:
                        logging.error(f"Unable to sent code for {self.phone.id}. Exception: {ex}.")
                        
                        self.phone.session = None
                        self.phone.is_banned = True
                        self.phone.is_verified = False
                        self.phone.code = None
                        self.phone.code_hash = None
                        
                        new_phone['session'] = self.phone.session
                        new_phone['isBanned'] = self.phone.is_banned
                        new_phone['isVerified'] = self.phone.is_verified
                        new_phone['code'] = self.phone.code
                        
                        break
                else:
                    await asyncio.sleep(10)
            else:
                logging.debug(f"Phone {self.phone.id} actually authorized.")
                
                break
                
        internal_id = await self.get_internal_id()
        
        if internal_id != None and internal_id != self.phone.internal_id:
            self.phone.internal_id = internal_id
            
            new_phone['internalId'] = self.phone.internal_id
            
        if len(new_phone.items()) > 1:
            ApiProcessor().set('phone', new_phone)
            
        self.phone.authorization_thread = None
                
    def run(self):
        asyncio.run(self.async_run())
