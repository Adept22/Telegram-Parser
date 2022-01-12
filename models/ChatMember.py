from models.Entity import Entity
from models.Chat import Chat

class ChatMember(Entity):
    api_path = 'member'
    
    def __init__(self, _dict):
        super().__init__(_dict)
        
        self._chat = None
        self._member = None
        self.is_left = False
        
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