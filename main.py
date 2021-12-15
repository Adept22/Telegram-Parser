import time
import requests
from processors.ChannelsListProcessor import ChannelsListProcessor
from parsers.HistoryParser import HistoryParser
from parsers.UsersParser import UsersParser
from processors.ApiProcessor import ApiProcessor

if __name__ == '__main__':
    api = ApiProcessor()
    
    while True:
        try:
            print('Пытаюсь получить чаты...')
            chats = api.get('chat')

            print('Чаты получены.')
            print(chats)

        except requests.exceptions.RequestException as ex:
            print('Возникла не обрабатываемая ошибка')
            raise SystemExit(ex)
            
        print('Жду 20 секунд.')
        time.sleep(20)

    # processor = ChannelsListProcessor()
    # channels = processor.get_unparsed_links()
    # total_links = len(channels)
    # for index, channel in enumerate(channels):
    #     if 'history' in channel and channel['history']:
    #         history_parser = HistoryParser(channel_link=channel['link'])
    #         history_parser.parse()
    #     if 'users' in channel and channel['users']:
    #         users_parser = UsersParser(channel_link=channel['link'])
    #         users_parser.parse()
    #     updated_channel = channel
    #     updated_channel['parsed'] = True
    #     processor.update_item(updated_channel)
