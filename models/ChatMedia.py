from models.Entity import Entity
from models.Chat import Chat

class ChatMedia(Entity):
    api_path = 'chat-media'
    
    def __init__(self, _dict):
        super().__init__(_dict)
        
        self._chat = None
        self.path = None
        
        self.from_dict()
    
    @property
    def chat(self):
        return self._chat
    
    @chat.setter
    def chat(self, new_chat):
        self._chat = self.from_api(Chat, new_chat)