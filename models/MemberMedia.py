from models.Entity import Entity
from models.Member import Member

class MemberMedia(Entity):
    api_path = 'member-media'
    
    def __init__(self, _dict):
        super().__init__(_dict)
        
        self._member = None
        self.path = None
        
        self.from_dict()
    
    @property
    def member(self):
        return self._member
    
    @member.setter
    def member(self, new_member):
        self._member = self.from_api(Member, new_member)