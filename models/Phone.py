import os
import re
import logging
import asyncio

from utils.bcolors import bcolors
from telethon import sync
from processors.ApiProcessor import ApiProcessor
from threads.SendCodeThread import SendCodeThread

class Phone(object):
    def __init__(self, dict):
        if dict is None:
            raise Exception('Unexpected phone dictionary')
            
        if not 'id' in dict or dict['id'] is None:
            raise Exception('Unexpected phone id')

        if not 'number' in dict or dict['number'] is None:
            raise Exception('Unexpected phone number')
        
        self.dict = dict
        
        self.code = None
        self.code_hash = None
        self.send_code_task = None
        
        self.client = sync.TelegramClient(
            session=f"sessions/{dict['number']}.session", 
            api_id=os.environ['TELEGRAM_API_ID'],
            api_hash=os.environ['TELEGRAM_API_HASH']
        )
        
        self.chats = {}
        
        self.from_dict(dict)
        
    def from_dict(self, dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in dict:
            setattr(self, pattern.sub('_', key).lower(), dict[key])
            
        return self
    
    async def init(self):
        if self.id == None:
            raise Exception("Undefined phone id")
        
        if not self.client.is_connected():
            await self.connect()
        
        is_user_authorized = await self.client.is_user_authorized()
        
        print(f"Phone {self.id} is authorized {is_user_authorized}.")
        logging.debug(f"Phone {self.id} is authorized {is_user_authorized}.")
        
        if not is_user_authorized:
            if self.code != None and self.code_hash != None:
                await self.sign_in()
            elif self.code_hash == None:
                if self.send_code_task == None:
                    self.send_code_task = SendCodeThread(self.id, self.number, asyncio.new_event_loop())
                    self.send_code_task.start()
        else:
            if self.send_code_task == None and not self.is_verified or self.code != None or self.code_hash != None:
                ApiProcessor().set('phone', { 'id': self.id, 'isVerified': True, 'code': None, 'codeHash': None })
                
            if self.send_code_task != None:
                self.send_code_task = None
            
        return self
    
    async def connect(self):
        print(f"Try connect phone {self.id}.")
        logging.debug(f"Try connect phone {self.id}.")
        
        await self.client.connect()
    
        print(f"Phone {self.id} connected.")
        logging.debug(f"Phone {self.id} connected.")
    
    async def sign_in(self):
        print(f"Phone {self.id} automatic try to sing in with code {self.code}.")
        logging.debug(f"Phone {self.id} automatic try to sing in with code {self.code}.")
        
        try:
            await self.client.sign_in(
                phone=self.number, 
                code=self.code, 
                phone_code_hash=self.code_hash
            )
        except Exception as ex:
            print(f"{bcolors.FAIL}Cannot authentificate phone {self.id} with code {self.code}. Exception: {ex}.{bcolors.ENDC}")
            logging.error(f"Cannot authentificate phone {self.id} with code {self.code}. Exception: {ex}.")
        else:
            ApiProcessor().set('phone', { 'id': self.id, 'isVerified': True, 'code': None, 'codeHash': None })
            
        ApiProcessor().set('phone', { 'id': self.id, 'isVerified': False, 'code': None })
    
    # async def get_chats(self):
    #     print(f"Getting chats for phone: {self.id}.")
    #     logging.debug(f"Getting chats for phone: {self.id}.")
        
    #     chats = ApiProcessor.get('chat', { 'phones': { 'id': self.id } })
        
    #     print(f"Getted {len(chats)} chats for phone: {self.id}.")
    #     logging.debug(f"Getted {len(chats)} chats for phone: {self.id}.")
        
    #     for chat in chats:
    #         if not chat['id'] in self.chats:
    #             chat = Chat(chat)
    #         else:
    #             chat = self.chats[chat['id']]
                
    #         if ChatsManager().get(chat['id']) == None:
    #             ChatsManager()[chat['id']] = chat
    #         else:
    #             ChatsManager()[chat['id']].from_dict(chat)
                
    #         chat.parse()