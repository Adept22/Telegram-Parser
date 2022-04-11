from models.MediaEntity import Media
from processors.ApiProcessor import ApiProcessor
from errors.UniqueConstraintViolationError import UniqueConstraintViolationError

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.MemberEntity import Member

class MemberMedia(Media):
    def __init__(self, internalId: 'int', member: 'Member' = None, id = None, path = None, date = None):
        self.id = id
        self.member = member
        self.internalId = internalId
        self.path = path
        self.date = date
    
    @property
    def download_path(self):
        return "./downloads/members"
    
    @property
    def name(self):
        return "member"
    
    @property
    def entity(self):
        return self.member

    def serialize(self):
        _dict = {
            "id": self.id,
            "member": self.member.serialize(),
            "internalId": self.internalId,
            "path": self.path,
            "date": self.date,
        }

        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict'):
        self.id = _dict.get("id")
        self.member = self.member.deserialize(_dict.get("member")) if self.member != None and "member" in _dict else None
        self.internalId = _dict.get("internalId")
        self.path = _dict.get("path")
        self.date = _dict.get("date")

        return self

    def save(self):
        if self.member.id == None:
            self.member.save()

        try:
            self.deserialize(ApiProcessor().set('telegram/member-media', self.serialize()))
        except UniqueConstraintViolationError:
            medias = ApiProcessor().get('telegram/member-media', { 'internalId': self.internalId })
            
            if len(medias) > 0:
                self.id = medias[0]['id']
                
                self.save()

        return self
