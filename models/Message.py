from models.Entity import Entity
from models.Chat import Chat
from models.ChatMember import ChatMember

class Message(Entity):
    api_path = 'message'
    
    def __init__(self, _dict):
        super().__init__(_dict)
        
        self.internal_id = None
        self.text = None
        self._chat = None
        self._member = None
        self._reply_to = None
        self.is_pinned = False
        self.forwarded_from_id = None
        self.forwarded_from_name = None
        self.grouped_id = None
        
        self.from_dict()
        
    @property
    def chat(self):
        return self._chat
    
    @chat.setter
    def chat(self, new_chat):
        self._chat = self.from_api(Chat, new_chat)
        
    @property
    def member(self):
        return self._member
    
    @member.setter
    def member(self, new_member):
        self._member = self.from_api(ChatMember, new_member)
        
    @property
    def reply_to(self):
        return self._reply_to
    
    @reply_to.setter
    def reply_to(self, new_reply_to):
        self._reply_to = self.from_api(Message, new_reply_to)