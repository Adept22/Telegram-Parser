import multiprocessing, typing
import entities, threads, helpers

if typing.TYPE_CHECKING:
    from threads import ChatProcess, ChatInfoThread, MembersThread, MessagesThread

class Chat(entities.Entity):
    def __init__(
        self,  
        id: 'str', 
        link: 'str', 
        isAvailable: 'bool', 
        internalId: 'int' = None, 
        title: 'str' = None, 
        description: 'str' = None, 
        date: 'str' = None, 
        *args, 
        **kwargs
    ):
        self.id: 'str' = id
        self.link: 'str' = link
        self.isAvailable: 'bool' = isAvailable
        self.__iternaId_condition = multiprocessing.Condition()
        self._internalId: 'int | None' = None
        self.internalId: 'int | None' = internalId
        self.title: 'str | None' = title
        self.description: 'str | None' = description
        self.date: 'str | None' = date

        self.username, self.hash = helpers.get_hash(link)

        self.phones: 'entities.TypeChatPhonesList[entities.TypeChatPhone]' = entities.ChatPhonesList()

        self.chat_init_thread: 'ChatProcess | None' = None

        self.chat_info_process: 'ChatInfoThread | None' = None
        self.members_process: 'MembersThread | None' = None
        self.messages_process: 'MessagesThread | None' = None

    # def __del__(self):
    #     self.chat_init_thread.terminate()
    #     self.chat_info_process.terminate()
    #     self.members_process.terminate()
    #     self.messages_process.terminate()

    def __call__(self, *args: 'typing.Any', **kwds: 'typing.Any') -> 'Chat':
        if self.chat_info_process == None or not self.chat_info_process.is_alive():
            self.chat_info_process = threads.ChatInfoThread(self)
            self.chat_info_process.start()

        if self.members_process == None or not self.members_process.is_alive():
            self.members_process = threads.MembersThread(self)
            self.members_process.start()

        # if self.messages_process == None or not self.messages_process.is_alive():
        #     self.messages_process = threads.MessagesThread(self)
        #     self.messages_process.start()

        return self
        
    @property
    def name(self) -> 'str':
        return "chat"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return None
        
    @property
    def internalId(self) -> 'int | None':
        with self.__iternaId_condition:
            while self._internalId == None or self._internalId > 0:
                self.__iternaId_condition.wait()
                
        return self._internalId
        
    @internalId.setter
    def internalId(self, new_value: 'int | None') -> 'int | None':
        with self.__iternaId_condition:
            self._internalId = new_value
            
            if self._internalId != None:
                if self._internalId < 0:
                    self.__iternaId_condition.notify_all()

    def serialize(self) -> 'dict':
        _dict =  {
            "id": self.id,
            "link": self.link,
            "isAvailable": self.isAvailable,
            "internalId": self.internalId,
            "title": self.title,
            "description": self.description,
            "date": self.date
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'Chat':
        self.id = _dict['id']
        self.link = _dict['link']
        self.isAvailable = _dict['isAvailable']
        self.internalId = _dict.get('internalId')
        self.title = _dict.get('title')
        self.description = _dict.get('description')
        self.date = _dict.get('date')

        return self
