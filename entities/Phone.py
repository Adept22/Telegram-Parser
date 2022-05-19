import entities

class Phone(entities.Entity):
    def __init__(
        self, 
        id: 'str', 
        number: 'str', 
        internalId: 'int' = None, 
        session: 'str' = None, 
        firstName: 'str' = None, 
        lastName: 'str' = None, 
        isVerified: 'bool' = False, 
        isBanned: 'bool' = False, 
        code: 'str' = None, 
        *args, 
        **kwargs
    ):
        self.id: 'str' = id
        self.number: 'str' = number
        self.internalId: 'int | None' = internalId
        self.session: 'str | None' = session
        self.firstName: 'str | None' = firstName
        self.lastName: 'str | None' = lastName
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
        return {
            "id": self.id,
            "number": self.number,
            "internalId": self.internalId,
            "session": self.session,
            "firstName": self.firstName,
            "lastName": self.lastName,
            "isVerified": self.isVerified,
            "isBanned": self.isBanned,
            "code": self.code
        }

    def deserialize(self, _dict: 'dict') -> 'entities.TypePhone':
        self.id = _dict["id"]
        self.number = _dict["number"]
        self.internalId = _dict.get("internalId")
        self.session = _dict.get("session")
        self.firstName = _dict.get("firstName")
        self.lastName = _dict.get("lastName")
        self.isVerified = _dict.get("isVerified", False)
        self.isBanned = _dict.get("isBanned", False)
        self.code = _dict.get("code")

        return self
        