import logging
import queue
import re
import asyncio
import threading
import globalvars

from telethon import sync, sessions
from models.Entity import Entity
from processors.ApiProcessor import ApiProcessor

from threads.JoinThread import JoinThread
from threads.AuthorizationThread import AuthorizationThread
from errors.ClientNotAvailableError import ClientNotAvailableError

class Phone(Entity):
    def __init__(self, _dict):
        if _dict is None:
            raise Exception('Unexpected phone dictionary')
            
        if not 'id' in _dict or _dict['id'] is None:
            raise Exception('Unexpected phone id')

        if not 'number' in _dict or _dict['number'] is None:
            raise Exception('Unexpected phone number')
        
        self.code_hash = None

        self._internal_id = None
        self._is_verified = False
        self._code = None
        self._session = None
        self._is_banned = False

        self.session_lock = threading.Lock()

        self.init_event = threading.Event()

        self.authorization_thread = None
        self.join_thread = None
        
        self.joining_queue = queue.Queue()
        
        self.from_dict(_dict)

    def __del__(self):
        # TODO: Мы должны убивать треды при удалении чата.
        pass

    def serialize(self):
        _dict = {
            "id": self.id,
            "internalId": self._internal_id,
            "session": self._session,
            "number": self.number,
            "username": self.username,
            "firstName": self.first_name,
            "isVerified": self._is_verified,
            "isBanned": self._is_banned,
            "code": self._code
        }
        
        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict'):
        return self

    @property
    def internal_id(self):
        return self._internal_id

    @internal_id.setter
    def internal_id(self, new_value):
        if new_value != None and self._internal_id != new_value:
            logging.info(f"Phone {self.id} internal_id changed.")

            ApiProcessor().set('telegram/phone', {'id': self.id, 'internalId': new_value})

        self._internal_id = new_value

    @property
    def is_verified(self):
        return self._is_verified

    @is_verified.setter
    def is_verified(self, new_value):
        if self._is_verified != new_value:
            logging.info(f"Phone {self.id} is_verified changed.")

            ApiProcessor().set('telegram/phone', {'id': self.id, 'isVerified': new_value})

        self._is_verified = new_value

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, new_value):
        if self._code != new_value:
            logging.info(f"Phone {self.id} code changed.")

            ApiProcessor().set('telegram/phone', {'id': self.id, 'code': new_value})

        self._code = new_value

    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, new_value):
        if self._session != new_value:
            logging.info(f"Phone {self.id} session changed.")

            ApiProcessor().set('telegram/phone', {'id': self.id, 'session': new_value})

        self._session = new_value

    @property
    def is_banned(self):
        return self._is_banned

    @is_banned.setter
    def is_banned(self, new_value):
        if self._is_banned != new_value:
            logging.info(f"Phone {self.id} is_banned changed.")

            ApiProcessor().set('telegram/phone', {'id': self.id, 'isBanned': new_value})

        self._is_banned = new_value
        
    def from_dict(self, _dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in _dict:
            setattr(self, pattern.sub('_', key).lower(), _dict[key])
            
        return self
    
    async def new_client(self, loop = asyncio.get_event_loop()):
        with self.session_lock:
            client = sync.TelegramClient(
                session=sessions.StringSession(self.session), 
                api_id=globalvars.parser['api_id'],
                api_hash=globalvars.parser['api_hash'],
                loop=loop
            )
            
            try:
                if not client.is_connected():
                    await client.connect()
                
                if await client.is_user_authorized():
                    await client.get_me()
                    
                    return client
                else:
                    if not self.authorization_thread.is_alive():
                        self.authorization_thread.start()

                    raise ClientNotAvailableError(f'Phone {self.id} not authorized')
            except Exception as ex:
                raise ClientNotAvailableError(ex)

    def run(self):
        self.authorization_thread = AuthorizationThread(self)
        self.authorization_thread.start()

        self.join_thread = JoinThread(self)
        self.join_thread.start()

        return self