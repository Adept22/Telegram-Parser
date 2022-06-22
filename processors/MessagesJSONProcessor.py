from processors.JSONFileProcessor import JSONFileProcessor
from config import BASE_DIR, MESSAGES_JSON_FILENAME
from models.errors.MessageValidationError import MessageValidationError
import os


class MessagesJSONProcessor():
    def __init__(self, channel_name):
        self.processor = JSONFileProcessor(os.path.join(BASE_DIR, f'results/{channel_name}/messages/{MESSAGES_JSON_FILENAME}'))

    def read_list(self):
        return self.processor.read()

    def get_id_list(self):
        messages_list = self.read_list()
        return list(map(lambda item: item['id'], messages_list))

    def get_last_id(self):
        ids = self.get_id_list()
        if not len(ids):
            return 0
        return max(ids)

    def add_message(self, message):
        self.processor.add_item(message.serialize())

    def check_item_in_list(self, message):
        messages_list = self.read_list()
        try:
            result_list = list(filter(lambda item: item['date'] == message.date and item['message'] == message.message, messages_list))
            return len(result_list)
        except KeyError:
            raise MessageValidationError
