from processors.JSONFileProcessor import JSONFileProcessor
from config import TAGS_LIST_JSON_FILENAME, BASE_DIR
import os


class TagsListProcessor():
    def __init__(self):
        self.processor = JSONFileProcessor(os.path.join(BASE_DIR, TAGS_LIST_JSON_FILENAME))

    def read_list(self):
        return self.processor.read()

    def add_tag(self, tag):
        self.processor.add_item(tag)

    def remove_tag(self, tag):
        self.processor.remove_item(tag)

    def is_tag_in_message(self, message):
        tags = self.read_list()
        if not len(tags):
            return 'Без ключевых слов'
        upper_message = message.upper()
        for tag in tags:
            if tag.upper() in upper_message:
                return tag
        return False
