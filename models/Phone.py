import os
import re
import logging

from telethon import sync, sessions

from utils import bcolors
from processors.ApiProcessor import ApiProcessor
from threads.SendCodeThread import SendCodeThread
from errors.ClientNotAvailableError import ClientNotAvailableError

class Phone(object):
    def __init__(self, dict):
        if dict is None:
            raise Exception('Unexpected phone dictionary')
            
        if not 'id' in dict or dict['id'] is None:
            raise Exception('Unexpected phone id')

        if not 'number' in dict or dict['number'] is None:
            raise Exception('Unexpected phone number')
        
        self.dict = dict
        
        self.code = None
        self.code_hash = None
        self.send_code_thread = None
        self._session = sessions.StringSession()
        
        self.from_dict(dict)
        
        self.client = sync.TelegramClient(
            session=self.session, 
            api_id=os.environ['TELEGRAM_API_ID'],
            api_hash=os.environ['TELEGRAM_API_HASH'],
        )
        
    @property
    def session(self):
        return self._session
    
    @session.setter
    def session(self, new_session):
        self._session = sessions.StringSession(new_session)
    
    async def new_client(self, loop = None):
        client = sync.TelegramClient(
            session=self.session, 
            api_id=os.environ['TELEGRAM_API_ID'],
            api_hash=os.environ['TELEGRAM_API_HASH'],
            loop=loop
        )
        
        try:
            if not client.is_connected():
                await client.connect()
            
            if await client.is_user_authorized():
                await client.get_me()
                
                return client
            else:
                raise ClientNotAvailableError(f'Phone {self.id} not authorized.')
        except Exception as ex:
            logging.error(f"Can\'t get phone {self.id} client. Exception: {ex}")
            
            raise ClientNotAvailableError(ex)
        
    def from_dict(self, dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in dict:
            setattr(self, pattern.sub('_', key).lower(), dict[key])
            
        return self
    
    async def init(self):
        if self.id == None:
            raise Exception("Undefined phone id")
        
        if not self.client.is_connected():
            await self.client.connect()
        
        is_user_authorized = await self.client.is_user_authorized()
        
        logging.debug(f"Phone {self.id} is authorized {is_user_authorized}.")
        
        if not is_user_authorized:
            if self.code != None and self.code_hash != None:
                await self.sign_in()
            elif self.code_hash == None:
                if self.send_code_thread == None:
                    self.send_code_thread = SendCodeThread(self)
                    self.send_code_thread.setDaemon(True)
                    self.send_code_thread.start()
        else:
            self.send_code_thread = None
            
            if not self.is_verified or self.code != None or self.code_hash != None:
                ApiProcessor().set('phone', { 'id': self.id, 'isVerified': True, 'code': None, 'codeHash': None })        
            
        return self
        
    async def sign_in(self):
        logging.debug(f"Phone {self.id} automatic try to sing in with code {self.code}.")
        
        try:
            await self.client.sign_in(
                phone=self.number, 
                code=self.code, 
                phone_code_hash=self.code_hash
            )
        except Exception as ex:
            logging.error(f"Cannot authentificate phone {self.id} with code {self.code}. Exception: {ex}.")
            
            ApiProcessor().set('phone', { 'id': self.id, 'session': None, 'isVerified': False, 'code': None })
        else:
            ApiProcessor().set('phone', { 'id': self.id, 'session': self.session.save(), 'isVerified': True, 'code': None, 'codeHash': None })
    