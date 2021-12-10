class ChannelListItemDTO():
    def __init__(self, name, link, history=True, users=True, parsed=False):
        self.name = name
        self.link = link
        self.history = history
        self.users = users
        self.parsed = parsed

    def serialize(self):
        result_object = {}
        for key in self.__dict__.keys():
            result_object[key] = self.__dict__[key]
        return result_object
