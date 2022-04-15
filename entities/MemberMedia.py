import entities

class MemberMedia(entities.Entity, entities.Media):
    def __init__(self, internalId: 'int', member: 'entities.TypeMember' = None, id = None, path = None, date = None, *args, **kwargs):
        self.id: 'str | None' = id
        self.member: 'entities.TypeMember | None' = member
        self.internalId: 'int' = internalId
        self.path: 'str | None' = path
        self.date: 'str | None' = date
    
    @property
    def download_path(self) -> 'str':
        return "./downloads/members"
    
    @property
    def name(self) -> 'str':
        return "member-media"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return { 'internalId': self.internalId }

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "member": { "id": self.member.id } if self.member != None and self.member.id != None else None,
            "internalId": self.internalId,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypeMemberMedia':
        self.id = _dict.get("id")
        self.member = self.member.deserialize(_dict.get("member")) if self.member != None and "member" in _dict else None
        self.internalId = _dict.get("internalId")
        self.path = _dict.get("path")
        self.date = _dict.get("date")

        return self
