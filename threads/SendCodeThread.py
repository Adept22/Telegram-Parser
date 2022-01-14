import os
import threading
import asyncio
import logging
from utils import bcolors

from telethon import sync, errors
from processors.ApiProcessor import ApiProcessor

class SendCodeThread(threading.Thread):
    def __init__(self, phone):
        threading.Thread.__init__(self, name=f'SendCodeThread-{phone.id}')
        
        self.phone = phone
        self.loop = asyncio.new_event_loop()
        
        asyncio.set_event_loop(self.loop)
        
    async def async_run(self):
        try:
            client = sync.TelegramClient(
                session=self.phone.session, 
                api_id=os.environ['TELEGRAM_API_ID'],
                api_hash=os.environ['TELEGRAM_API_HASH'],
                loop=self.loop
            )

            if not client.is_connected():
                await client.connect()
                
            logging.debug(f"SendCodeThread: Sending code for {self.phone.id}.")
            
            sent = await client.send_code_request(phone=self.phone.number)
            
            ApiProcessor().set('phone', { 'id': self.phone.id, 'isVerified': False, 'code': None, 'codeHash': sent.phone_code_hash })
            
            logging.info(f"SendCodeThread: code sended for {self.phone.id}.")
        except errors.rpcerrorlist.FloodWaitError as ex:
            logging.warning(f"SendCodeThread: flood exception for {self.phone.id}. Sleep {ex.seconds}.")
            
            await asyncio.sleep(ex.seconds)
            
            await self.async_run()
        except Exception as ex:
            logging.error(f"SendCodeThread: unable to sent code for {self.phone.id}. Exception: {ex}.")
            
            # TODO: Открыть после всех тестов
            # ApiProcessor().set('phone', { 'id': self.phone.id, 'isBanned': True, 'code': None, 'codeHash': None })  

    def run(self):
        asyncio.run(self.async_run())
