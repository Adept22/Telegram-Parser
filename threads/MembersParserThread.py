import os
import logging
import threading
import asyncio
from telethon.errors import ChatAdminRequiredError

from config import USER_FIELDS, BASE_DIR, USERS_XLSX_FILENAME
from processors.UsersJSONProcessor import UsersJSONProcessor
from processors.XLSXFileProcessor import XLSXFileProcessor
from models.User import User

class MembersParserThread(threading.Thread):
    def __init__(self, chat, client, loop):
        print(f"Creating chat {self.chat.id} parsing thread...")
        logging.debug(f"Creating chat {self.chat.id} parsing thread...")
        
        threading.Thread.__init__(self)
        
        self.chat = chat
        self.client = client
        self.loop = loop
    
    async def async_run(self):
        result_users = []
        
        try:
            users = await self.client.get_participants(self.chat)
        except:
            print(f'Catched exception while getting participants for chat {self.chat.id}. Sleeping 10 sec and trying again.')
            logging.info(f'Catched exception while getting participants for chat {self.chat.id}. Sleeping 10 sec and trying again.')
            
            await asyncio.sleep(10)
        
        await asyncio.sleep(1)
        
        users_count = len(users)

        for index, user in enumerate(users):
            print(f'Chat {self.chat.id}. Receiving users... {index + 1} in {users_count}.')
            logging.info(f'Chat {self.chat.id}. Receiving users... {index + 1} in {users_count}.')
            
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