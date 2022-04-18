import asyncio, typing, telethon, telethon.sessions
import multiprocessing
import globalvars, entities, exceptions, processes

if typing.TYPE_CHECKING:
    from telethon import TelegramClient
    from processes import AuthorizationProcess, JoinChatsProcess

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

        self._is_authorized = False
        self._is_authorized_condition = multiprocessing.Condition()
        self.authorization_process: 'AuthorizationProcess | None' = None

        self._join_queue = multiprocessing.Queue()
        self.join_chats_thread: 'JoinChatsProcess | None' = None

    # def __del__(self):
    #     self.authorization_process.terminate()
    #     self.join_chats_thread.terminate()

    def __call__(self, *args: 'typing.Any', **kwds: 'typing.Any') -> 'entities.TypePhone':
        if self.authorization_process == None or not self.authorization_process.is_alive():
            self.authorization_process = processes.AuthorizationProcess(self)
            self.authorization_process.start()

        if self.join_chats_thread == None or not self.join_chats_thread.is_alive():
            self.join_chats_thread = processes.JoinChatsProcess(self)
            self.join_chats_thread.start()
        
        return self

    @property
    def name(self) -> 'str':
        return "phone"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return None
        
    @property
    def is_authorized(self) -> 'bool':
        with self._is_authorized_condition:
            while not self._is_authorized:
                self._is_authorized_condition.wait()
                
            return self._is_authorized
        
    @is_authorized.setter
    def is_authorized(self, new_value) -> 'None':
        with self._is_authorized_condition:
            self._is_authorized = new_value
            
            if self._is_authorized:
                self._is_authorized_condition.notify_all()

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
        try:
            if self.is_authorized:
                client = telethon.TelegramClient(
                    session=telethon.sessions.StringSession(self.session), 
                    api_id=globalvars.parser['api_id'],
                    api_hash=globalvars.parser['api_hash'],
                    loop=loop
                )
                
                try:
                    if not client.is_connected():
                        await client.connect()
                except OSError as ex:
                    raise exceptions.ClientNotAvailableError(str(ex))
                else:
                    if await client.is_user_authorized() and await client.get_me() != None:
                        return client
            raise exceptions.ClientNotAvailableError(f'Phone {self.id} not authorized')
        except exceptions.ClientNotAvailableError as ex:
            self.is_authorized = False
            self()

    def join_chat(self, chat: 'entities.TypeChat') -> 'None':
        self._join_queue.put(chat)
