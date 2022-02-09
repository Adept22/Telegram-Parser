import os
import re
import asyncio
import logging
import threading

from telethon import sync, sessions

from processors.ApiProcessor import ApiProcessor
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
        
        self.internal_id = None
        self.code = None
        self.code_hash = None
        self.session = None

        self.run_event = threading.Event()

        self.joining_lock = threading.Lock()
        
        self.from_dict(dict)

    def __del__(self):
        if self.run_event.is_set():
            self.run_event.clear()
        # TODO: Мы должны убивать треды при удалении чата.
        pass
    
    async def new_client(self, loop = asyncio.get_event_loop()):
        client = sync.TelegramClient(
            session=sessions.StringSession(self.session), 
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
                raise ClientNotAvailableError(f'Phone {self.id} not authorized')
        except Exception as ex:
            raise ClientNotAvailableError(ex)
        
    def from_dict(self, dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in dict:
            setattr(self, pattern.sub('_', key).lower(), dict[key])
            
        return self

    def run(self):
        self.authorization_thread = AuthorizationThread(self)
        self.authorization_thread.setDaemon(True)
        self.authorization_thread.start()

        return self