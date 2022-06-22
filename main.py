from processors.ChannelsListProcessor import ChannelsListProcessor
from parsers.HistoryParser import HistoryParser
from parsers.UsersParser import UsersParser

if __name__ == '__main__':
    processor = ChannelsListProcessor()
    channels = processor.get_unparsed_links()
    total_links = len(channels)
    for index, channel in enumerate(channels):
        if 'history' in channel and channel['history']:
            history_parser = HistoryParser(channel_link=channel['link'])
            history_parser.parse()
        if 'users' in channel and channel['users']:
            users_parser = UsersParser(channel_link=channel['link'])
            users_parser.parse()
        updated_channel = channel
        updated_channel['parsed'] = True
        processor.update_item(updated_channel)
