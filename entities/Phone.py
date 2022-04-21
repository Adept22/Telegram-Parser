import asyncio, typing, telethon, telethon.sessions
import globalvars, entities, exceptions

if typing.TYPE_CHECKING:
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

        # self._is_authorized = False
        # self.__is_authorized_condition = multiprocessing.Condition()

    # def __del__(self):
    #     self.authorization_thread.terminate()
    #     self.join_chats_thread.terminate()

    @property
    def name(self) -> 'str':
        return "phone"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return None
        
    # @property
    # def is_authorized(self) -> 'bool':
    #     with self.__is_authorized_condition:
    #         while not self._is_authorized:
    #             self.__is_authorized_condition.wait()
                
    #         return self._is_authorized
        
    # @is_authorized.setter
    # def is_authorized(self, new_value) -> 'None':
    #     with self.__is_authorized_condition:
    #         self._is_authorized = new_value
            
    #         if self._is_authorized:
    #             self.__is_authorized_condition.notify_all()

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
        