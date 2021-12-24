import asyncio
import threading
import logging
import os.path

from models.Message import Message
from telethon.tl.functions.messages import GetHistoryRequest
from config import HISTORY_PARSE_DEPTH, MESSAGE_FIELDS, BASE_DIR, MESSAGES_XLSX_FILENAME
from processors.MessagesJSONProcessor import MessagesJSONProcessor
from processors.XLSXFileProcessor import XLSXFileProcessor
from core.ClientFactory import ClientFactory

from models.errors.MessageValidationError import MessageValidationError


class MessagesParserThread(threading.Thread):
    def __init__(self, chat, client, loop):
        print(f"Creating chat {self.chat.id} parsing thread...")
        logging.debug(f"Creating chat {self.chat.id} parsing thread...")
        
        threading.Thread.__init__(self)
        
        self.chat = chat
        self.client = client
        self.loop = loop

    async def dump_all_messages(self, channel):
        channel.title = channel.title.replace('/', '-')
        messages_processor = MessagesJSONProcessor(channel_name=channel.title)
        offset_msg = 0  # номер записи, с которой начинается считывание
        limit_msg = 1000  # максимальное число записей, передаваемых за один раз
        all_messages_count = 0  # список всех сообщений
        message_id = messages_processor.get_last_id() + 1
        result_messages = []
        total_count_limit = HISTORY_PARSE_DEPTH

        while True:
            await asyncio.sleep(2)
            print(f"Parsing {channel.title}... Received: {all_messages_count} messages.")
            history = await self.client(GetHistoryRequest(
                peer=channel,
                offset_id=offset_msg,
                offset_date=None, add_offset=0,
                limit=limit_msg, max_id=0, min_id=0,
                hash=0))
            if not history.messages:
                break
            messages = history.messages
            for message in messages:
                all_messages_count += 1
                try:
                    msg = Message(message)
                    msg.id = message_id
                    history_message = messages_processor.check_item_in_list(msg)
                    if not history_message:
                        await msg.enrich(channel=channel)
                        result_messages.append(msg.serialize())
                        messages_processor.add_message(msg)
                        message_id += 1
                except MessageValidationError:
                    pass
            offset_msg = messages[len(messages) - 1].id
            if total_count_limit != 0 and all_messages_count >= total_count_limit:
                break
        return result_messages

    async def async_run(self):
        channel = await self.client.get_entity(self.channel_link)
        channel.link = self.channel_link
        messages = await self.dump_all_messages(channel=channel)
        if not len(messages):
            return
        xlsx_processor = XLSXFileProcessor(fields_config=MESSAGE_FIELDS, xlsx_filename=os.path.join(BASE_DIR, f'results/{messages[0]["channel"]}/messages/{MESSAGES_XLSX_FILENAME}'))
        xlsx_processor.convert(messages)
        return messages

    def run(self):
        asyncio.run(self.async_run())