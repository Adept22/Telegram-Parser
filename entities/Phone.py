import entities

class Phone(entities.Entity):
    def __init__(self, id: 'str', number: 'str', internalId: 'int' = None, session: 'str' = None, username: 'str' = None, firstName: 'str' = None, isVerified: 'bool' = False, isBanned: 'bool' = False, code: 'str' = None, *args, **kwargs):
        self.id: 'str' = id
        self.number: 'str' = number
        self.internalId: 'int | None' = internalId
        self.session: 'str | None' = session
        self.username: 'str | None' = username
        self.firstName: 'str | None' = firstName
        self.isVerified: 'bool' = isVerified
        self.isBanned: 'bool' = isBanned
        self.code: 'str | None' = code
        
        self.code_hash: 'str | None' = None

    @property
    def name(self) -> 'str':
        return "phone"
        
    @property
    def unique_constraint(self) -> 'dict | None':
        return None

    def serialize(self) -> 'dict':
        _dict = {
            "id": self.id,
            "number": self.number,
            "internalId": self.internalId,
            "session": self.session,
            "username": self.username,
            "firstName": self.firstName,
            "isVerified": self.isVerified,
            "isBanned": self.isBanned,
            "code": self.code
        }
        
        return dict((k, v) for k, v in _dict.items() if v is not None)

    def deserialize(self, _dict: 'dict') -> 'entities.TypePhone':
        self.id = _dict["id"]
        self.number = _dict["number"]
        self.internalId = _dict.get("internalId")
        self.session = _dict.get("session")
        self.username = _dict.get("username")
        self.firstName = _dict.get("firstName")
        self.isVerified = _dict.get("isVerified", False)
        self.isBanned = _dict.get("isBanned", False)
        self.code = _dict.get("code")

        return self
        