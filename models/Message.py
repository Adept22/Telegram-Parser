from core.ClientFactory import ClientFactory
from datetime import timedelta
from processors.TagsListProcessor import TagsListProcessor
from processors.UsersJSONProcessor import UsersJSONProcessor
from models.errors.MessageValidationError import MessageValidationError
from models.User import User
from config import MESSAGE_FIELDS


class Message:
    def __init__(self, message_object):
        self.message_object = message_object
        self.message_dict = message_object.to_dict()
        if not 'message' in self.message_dict:
            raise MessageValidationError
        self.message = self.message_dict['message']
        tags_processor = TagsListProcessor()
        tag = tags_processor.is_tag_in_message(self.message)
        if not tag:
            raise MessageValidationError
        self.tag = tag
        self.date = format((self.message_dict['date'] + timedelta(hours=3)), "%Y.%m.%d, %H:%M:%S")
        self.client = ClientFactory().get_client()
        self.channel = None
        self.channel_link = None
        self.user = None
        self.link = None

    async def enrich(self, channel):
        try:
            self.channel = channel.title
            self.channel_link = channel.link
            if not 'joinchat' in self.channel_link:
                self.link = f'{self.channel_link}/{self.message_dict["id"]}'
            try:
               userId = self.message_dict['from_id']['user_id']
               user_object = await self.client.get_entity(userId)
               user = User(user_object)
            except TypeError:
                self.user = {'username': channel.title, 'id': channel.title}
                return
            users_processor = UsersJSONProcessor(channel_name=self.channel)
            history_user = users_processor.get_item_by_id(user.id)
            if history_user:
                self.user = history_user
            else:
                await user.enrich(channel=channel)
                self.user = user.serialize()
                users_processor.add_user(user)
            print(f'Cached message: {self.serialize()}')
        except KeyError:
            return
        except TypeError:
            raise MessageValidationError

    def serialize(self):
        result = {}
        keys = list(MESSAGE_FIELDS.keys())
        keys.append('user')
        for key in keys:
            if key in self.__dict__ and self.__dict__[key]:
                result[key] = self.__dict__[key]
        return result
