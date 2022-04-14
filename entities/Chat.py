import entities, helpers
from services import PhonesManager
from processes import ChatMediaProcess, MembersProcess, MessagesProcess

class Chat(entities.Entity):
    def __init__(
        self,  
        id: 'str', 
        link: 'str', 
        isAvailable: 'bool', 
        type: 'str' = None, 
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
        self.availablePhones: 'list[entities.TypePhone]' = [PhonesManager()[p['id']] for p in availablePhones if p['id'] in PhonesManager()]
        self.phones: 'list[entities.TypePhone]' = [PhonesManager()[p['id']] for p in phones if p['id'] in PhonesManager()]
        self.type: 'str | None' = type
        self.internalId: 'int | None' = internalId
        self.title: 'str | None' = title
        self.description: 'str | None' = description
        self.date: 'str | None' = date

        self.username, self.hash = helpers.get_hash(link)

        # TODO: list for phones with lock when empty
        self.chat_media_process = ChatMediaProcess(self)
        self.members_process = MembersProcess(self)
        self.messages_process = MessagesProcess(self)

        if len(self.phones) < 3 and len(self.availablePhones) > len(self.phones):
            a_ps = dict([(p.id, p) for p in self.availablePhones])
            phones = dict([(p.id, p) for p in self.phones])

            for id in list(set(a_ps) - set(phones)):
                a_ps[id].join_chat(self)
        
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
            "type": self.type,
            "description": self.description,
            "date": self.date,
            "availablePhones": [{ "id": p.id } for p in self.availablePhones],
            "phones": [{ "id": p.id } for p in self.phones],
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypeChat':
        self.id = _dict.get('id')
        self.link = _dict.get('link')
        self.isAvailable = _dict.get('isAvailable')
        self.availablePhones = [PhonesManager()[p['id']] for p in _dict.get('availablePhones', []) if p['id'] in PhonesManager()]
        self.phones = [PhonesManager()[p['id']] for p in _dict.get('phones', []) if p['id'] in PhonesManager()]
        self.internalId = _dict.get('internalId')
        self.type = _dict.get('type')
        self.title = _dict.get('title')
        self.description = _dict.get('description')
        self.date = _dict.get('date')

        return self

    def add_phone(self, phone: 'entities.TypePhone'):
        if not phone.id in [_p.id for _p in self.phones]:
            self.phones.append(phone)

    def remove_phone(self, phone: 'entities.TypePhone'):
        self.phones = [_p for _p in self.phones if _p.id != phone.id]

    def add_available_phone(self, phone: 'entities.TypePhone'):
        if not phone.id in [_p.id for _p in self.availablePhones]:
            self.availablePhones.append(phone)

    def remove_available_phone(self, phone):
        self.availablePhones = [_p for _p in self.availablePhones if _p.id != phone.id]
        
    def run(self) -> 'entities.TypePhone':
        self.chat_media_process.start()
        # self.members_process.start()
        # self.messages_process.start()

        return self
