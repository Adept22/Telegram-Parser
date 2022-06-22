from processors.JSONFileProcessor import JSONFileProcessor
from config import BASE_DIR, USERS_JSON_FILENAME
import os


class UsersJSONProcessor():
    def __init__(self, channel_name):
        self.processor = JSONFileProcessor(os.path.join(BASE_DIR, f'results/{channel_name}/users/{USERS_JSON_FILENAME}'))

    def read_list(self):
        return self.processor.read()

    def add_user(self, user):
        self.processor.add_item(user.serialize())

    def get_id_list(self):
        users_list = self.read_list()
        return list(map(lambda item: item['id'], users_list))

    def get_item_by_id(self, id):
        users_list = self.read_list()
        result_list = list(filter(lambda item: item['id'] == id, users_list))
        if len(result_list) > 0:
            return result_list[0]
        return None
