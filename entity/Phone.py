import re, multiprocessing, asyncio, queue, logging, telethon
import globalvars, entity, processes, exceptions
from services import ApiService

class Phone(entity.Entity):
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

        self.init_event = multiprocessing.Event()

        self.authorization_process = None
        self.join_process = None
        
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

            ApiService().set('telegram/phone', {'id': self.id, 'internalId': new_value})

        self._internal_id = new_value

    @property
    def is_verified(self):
        return self._is_verified

    @is_verified.setter
    def is_verified(self, new_value):
        if self._is_verified != new_value:
            logging.info(f"Phone {self.id} is_verified changed.")

            ApiService().set('telegram/phone', {'id': self.id, 'isVerified': new_value})

        self._is_verified = new_value

    @property
    def code(self):
        return self._code

    @code.setter
    def code(self, new_value):
        if self._code != new_value:
            logging.info(f"Phone {self.id} code changed.")

            ApiService().set('telegram/phone', {'id': self.id, 'code': new_value})

        self._code = new_value

    @property
    def session(self):
        return self._session

    @session.setter
    def session(self, new_value):
        if self._session != new_value:
            logging.info(f"Phone {self.id} session changed.")

            ApiService().set('telegram/phone', {'id': self.id, 'session': new_value})

        self._session = new_value

    @property
    def is_banned(self):
        return self._is_banned

    @is_banned.setter
    def is_banned(self, new_value):
        if self._is_banned != new_value:
            logging.info(f"Phone {self.id} is_banned changed.")

            ApiService().set('telegram/phone', {'id': self.id, 'isBanned': new_value})

        self._is_banned = new_value
        
    def from_dict(self, _dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in _dict:
            setattr(self, pattern.sub('_', key).lower(), _dict[key])
            
        return self
    
    async def new_client(self, loop = asyncio.get_event_loop()):
        client = telethon.TelegramClient(
            session=telethon.sessions.StringSession(self.session), 
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
                if not self.authorization_process.is_alive():
                    self.authorization_process.start()

                raise exceptions.ClientNotAvailableError(f'Phone {self.id} not authorized')
        except Exception as ex:
            raise exceptions.ClientNotAvailableError(ex)

    def run(self):
        self.authorization_process = processes.AuthorizationProcess(self)
        self.authorization_process.start()

        self.join_proces = processes.JoinChatProcess(self)
        self.join_proces.start()

        return self