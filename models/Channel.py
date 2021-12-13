from config import CHANNEL_FIELDS

class Channel:
    def __init__(self, channel_object):
        self.channel_dict = channel_object.to_dict()
        self.id = self.channel_dict['id']
        self.title = self.channel_dict['title']

    def serialize(self):
        result = {}
        keys = list(CHANNEL_FIELDS.keys())
        for key in keys:
            if key in self.__dict__ and self.__dict__[key]:
                result[key] = self.__dict__[key]
        return result
