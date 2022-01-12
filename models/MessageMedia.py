from models.Entity import Entity
from models.Message import Message

class MessageMedia(Entity):
    api_path = 'message-media'
    
    def __init__(self, _dict):
        super().__init__(_dict)
        
        self._message = None
        self.path = None
        
        self.from_dict()
    
    @property
    def message(self):
        return self._message
    
    @message.setter
    def message(self, new_message):
        self._message = self.from_api(Message, new_message)