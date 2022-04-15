import processes, entities, helpers

class Chat(entities.Entity):
    def __init__(
        self,  
        id: 'str', 
        link: 'str', 
        isAvailable: 'bool', 
        availablePhones: 'list[dict]' = [], 
        phones: 'list[dict]' = [], 
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
        self.availablePhones: 'entities.TypePhonesList' = entities.PhonesList(availablePhones)
        self.phones: 'entities.TypePhonesList' = entities.PhonesList(phones)
        self.internalId: 'int | None' = internalId
        self.title: 'str | None' = title
        self.description: 'str | None' = description
        self.date: 'str | None' = date

        self.username, self.hash = helpers.get_hash(link)

        self.chat_init_process = processes.ChatInitProcess(self)
        self.chat_init_process.start()
        self.chat_media_process = processes.ChatMediaProcess(self)
        self.chat_media_process.start()
        self.members_process = processes.MembersProcess(self)
        self.members_process.start()
        self.messages_process = processes.MessagesProcess(self)
        self.messages_process.start()

    def __del__(self):
        try:
            self.chat_init_process.kill()
        except ValueError:
            pass

        try:
            self.chat_media_process.kill()
        except ValueError:
            pass

        try:
            self.members_process.kill()
        except ValueError:
            pass

        try:
            self.messages_process.kill()
        except ValueError:
            pass
        
    @property
    def name(self) -> 'str':
        return "chat"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    def serialize(self) -> 'dict':
        _dict =  {
            "id": self.id,
            "link": self.link,
            "isAvailable": self.isAvailable,
            "internalId": self.internalId,
            "title": self.title,
            "description": self.description,
            "date": self.date,
            "availablePhones": [{ "id": p.id } for p in self.availablePhones],
            "phones": [{ "id": p.id } for p in self.phones],
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypeChat':
        self.id = _dict['id']
        self.link = _dict['link']
        self.isAvailable = _dict['isAvailable']
        self.availablePhones = entities.PhonesList(_dict['availablePhones'])
        self.phones = entities.PhonesList(_dict['phones'])
        self.internalId = _dict.get('internalId')
        self.title = _dict.get('title')
        self.description = _dict.get('description')
        self.date = _dict.get('date')

        return self
