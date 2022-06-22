class MessageValidationError(Exception):
    def __init__(self, message='Unvalid message. Skip it.'):
        self.message = message
        super().__init__(self.message)
