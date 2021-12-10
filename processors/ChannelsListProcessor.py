from processors.JSONFileProcessor import JSONFileProcessor
from config import CHANNELS_LIST_JSON_FILENAME, BASE_DIR
import os
from dto.ChannelListItemDTO import ChannelListItemDTO


class ChannelsListProcessor():
    def __init__(self):
        self.processor = JSONFileProcessor(os.path.join(BASE_DIR, CHANNELS_LIST_JSON_FILENAME))

    def read_list(self):
        return self.processor.read()

    def add_channel(self, channel):
        if isinstance(channel, ChannelListItemDTO):
            self.processor.add_item(channel.serialize())
        else:
            raise ValueError('chat must be an instance of ChatListItemDTO.')

    def get_names(self):
        chats_list = self.read_list()
        return list(map(lambda item: item['name'], chats_list))

    def get_links(self):
        chats_list = self.read_list()
        return list(map(lambda item: item['link'], chats_list))

    def get_unparsed_links(self):
        chats_list = self.read_list()
        return list(filter(lambda item: not item['parsed'], chats_list))

    def get_item_by_link(self, link):
        chats_list = self.read_list()
        result_list = list(filter(lambda item: item['link'] == link, chats_list))
        if len(result_list) > 0:
            return result_list[0]
        return None

    def get_item_by_name(self, name):
        chats_list = self.read_list()
        result_list = list(filter(lambda item: item['name'] == name, chats_list))
        if len(result_list) > 0:
            return result_list[0]
        return None

    def get_link_by_name(self, name):
        return self.get_item_by_name(name)['link']

    def get_name_by_link(self, link):
        return self.get_item_by_link(link)['name']

    def remove_channel_by_name(self, name):
        self.processor.remove_item(self.get_item_by_name(name))

    def remove_channel_by_link(self, link):
        self.processor.remove_item(self.get_item_by_link(link))

    def update_item(self, item):
        self.remove_channel_by_link(item['link'])
        self.add_channel(
            ChannelListItemDTO(
                name=item['name'],
                link=item['link'],
                users=item['users'],
                history=item['history'],
                parsed=item['parsed']
            )
        )
