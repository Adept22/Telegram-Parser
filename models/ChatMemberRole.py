from models.Entity import Entity
from models.ChatMember import ChatMember

class ChatMemberRole(Entity):
    api_path = 'chat-member-role'
    
    def __init__(self, _dict):
        super().__init__(_dict)
        
        self._member = None
        self.title = None
        self.code = None
        
        self.from_dict()
    
    @property
    def member(self):
        return self._member
    
    @member.setter
    def member(self, new_member):
        self._member = self.from_api(ChatMember, new_member)