import os
import random
import logging
import threading
import asyncio
from telethon import sync, functions, types

from config import USER_FIELDS, BASE_DIR, USERS_XLSX_FILENAME
from processors.UsersJSONProcessor import UsersJSONProcessor
from processors.XLSXFileProcessor import XLSXFileProcessor
from models.User import User

class MembersParserThread(threading.Thread):
    def __init__(self, chat, phones, loop):
        print(f"Creating chat {self.chat.id} parsing thread...")
        logging.debug(f"Creating chat {self.chat.id} parsing thread...")
        
        threading.Thread.__init__(self)
        
        self.chat = chat
        self.phones = phones
        self.loop = loop
        
        self.clients = [
            sync.TelegramClient(
                session=f"sessions/{phone.number}.session", 
                api_id=os.environ['TELEGRAM_API_ID'],
                api_hash=os.environ['TELEGRAM_API_HASH'],
                loop=self.loop
            ) for phone in self.phones
        ]
    
    async def async_run(self):
        for i, client in enumerate(self.clients):
            try:
                if not client.is_connected():
                    await client.connect()
            except:
                del self.clients[i]
                
        if len(self.clients) == 0:
            print(f'No available clients for chat {self.chat.id}.')
            logging.info(f'No available clients for chat {self.chat.id}.')
            
            return

        result_users = []
        
        for client in self.clients:
            try:
                users = await client(
                    functions.channels.GetParticipantsRequest(
                        types.InputChannel(channel_id=self.chat.internal_id, access_hash=self.chat.access_hash)
                    )
                )
            except:
                await asyncio.sleep(random.randint(2, 5))
                
                continue
            else:
                break
        else:
            raise Exception(f'Cannot get chat {self.chat.id} participants. Exit.')

        for index, user in enumerate(users):
            print(f'Chat {self.chat.id}. Receiving users... {index + 1} in {len(users)}.')
            logging.info(f'Chat {self.chat.id}. Receiving users... {index + 1} in {len(users)}.')
            
            user = User(user)
            
            users_processor = UsersJSONProcessor(channel_name=self.channel.title)
            history_user = users_processor.get_item_by_id(user.id)
            
            if history_user:
                result_users.append(history_user)
            else:
                await user.enrich(channel=self.channel)
                
                users_processor.add_user(user)
                
                result_users.append(user.serialize())

        if not len(result_users):
            return
        
        xlsx_processor = XLSXFileProcessor(fields_config=USER_FIELDS, xlsx_filename=os.path.join(BASE_DIR, f'results/{self.channel.title}/users/{USERS_XLSX_FILENAME}'))
        xlsx_processor.convert(result_users)
        
        return result_users
        
    def run(self):
        asyncio.run(self.async_run())