import asyncio, queue, telethon, telethon.sessions
import globalvars, entities, exceptions
from processes import AuthorizationProcess, JoinChatsProcess

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from telethon import TelegramClient

class Phone(entities.Entity):
    def __init__(self, id: 'str', number: 'str', internalId: 'int' = None, session: 'str' = None, username: 'str' = None, firstName: 'str' = None, isVerified: 'bool' = False, isBanned: 'bool' = False, code: 'str' = None, *args, **kwargs):
        self.id: 'str' = id
        self.number: 'str' = number
        self.internalId: 'int | None' = internalId
        self.session: 'str | None' = session
        self.username: 'str | None' = username
        self.firstName: 'str | None' = firstName
        self.isVerified: 'bool' = isVerified
        self.isBanned: 'bool' = isBanned
        self.code: 'str | None' = code
        
        self.code_hash: 'str | None' = None
        
        self.joining_queue = queue.Queue()

        self.authorization_process = AuthorizationProcess(self)
        self.join_chats_process = JoinChatsProcess(self)

    def __del__(self):
        # TODO: Мы должны убивать треды при удалении чата.
        pass

    @property
    def name(self) -> 'str':
        return "phone"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "number": self.number,
            "internalId": self.internalId,
            "session": self.session,
            "username": self.username,
            "firstName": self.firstName,
            "isVerified": self.isVerified,
            "isBanned": self.isBanned,
            "code": self.code
        }
        
        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypePhone':
        self.id = _dict["id"]
        self.number = _dict["number"]
        self.internalId = _dict.get("internalId")
        self.session = _dict.get("session")
        self.username = _dict.get("username")
        self.firstName = _dict.get("firstName")
        self.isVerified = _dict.get("isVerified", False)
        self.isBanned = _dict.get("isBanned", False)
        self.code = _dict.get("code")

        return self
    
    async def new_client(self, loop = asyncio.get_event_loop()) -> 'TelegramClient':
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

    def run(self) -> 'entities.TypePhone':
        self.authorization_process.start()
        self.join_chats_process.start()

        return self