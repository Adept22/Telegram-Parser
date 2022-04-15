class RequestException(Exception):
    def __init__(self, code=500, msg=None):
        Exception.__init__(self, f"Unexpected error {code}" if not msg else msg)
        self.msg = f"Unexpected error {code}" if not msg else msg
        self.code = code

    def __reduce__(self):
        return self.__class__, (self.msg, self.code)