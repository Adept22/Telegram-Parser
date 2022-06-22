import json
import os
from utils.DateTimeEncoder import DateTimeEncoder


class JSONFileProcessor:
    def __init__(self, json_filename):
        self.filename = json_filename
        if len(self.filename.split('/')) <= 2:
            self.path = self.filename
        else:
            self.path = '/'.join(self.filename.split('/')[:-1])

    def read(self):
        try:
            with open(self.filename, 'r', encoding='utf8') as file:
                return json.loads(file.read())
        except FileNotFoundError:
            self.write([])
            return []

    def write(self, items):
        isExist = os.path.exists(self.path)

        if not isExist:
            os.makedirs(self.path)
        with open(self.filename, 'w', encoding='utf8') as file:
            json.dump(items, file, ensure_ascii=False, cls=DateTimeEncoder)

    def add_item(self, item):
        try:
            current_content = self.read()
        except FileNotFoundError:
            self.write([])
            current_content = self.read()
        current_content.append(item)
        self.write(current_content)

    def remove_item(self, item):
        try:
            current_content = self.read()
        except FileNotFoundError:
            raise FileNotFoundError('File not found :(')
        index = current_content.index(item)
        if index != 0 and not index:
            raise ValueError('No such element')
        current_content.pop(index)
        self.write(current_content)

    def add_items(self, items):
        current_content = self.read()
        current_content += items
        self.write(current_content)

    def clear(self):
        self.write([])


