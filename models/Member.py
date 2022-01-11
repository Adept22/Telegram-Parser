from models.Entity import Entity

class Member(Entity):
    api_path = 'member'
    
    def __init__(self, _dict):
        super().__init__(_dict)
        
        self.internalId = None
        self.username = None
        self.firstName = None
        self.lastName = None
        self.about = None
        self.phone = None
        
        self.from_dict()
    