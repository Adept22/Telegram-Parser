import os
import re
import logging

from telethon import sync, sessions

from threads.AuthorizationThread import AuthorizationThread
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
        self._session = sessions.StringSession()
        self.authorization_thread = None
        
        self.from_dict(dict)
        
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
    
    def start_auth_thread(self):
        self.authorization_thread = AuthorizationThread(self)
        self.authorization_thread.setDaemon(True)
        self.authorization_thread.start()
    
    async def init(self):
        if self.session.save() == "":
            if self.authorization_thread == None:
                self.start_auth_thread()
            elif not self.authorization_thread.is_alive():
                self.start_auth_thread()
        else:
            self.authorization_thread == None
            
        return self
