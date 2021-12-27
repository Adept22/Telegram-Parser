import os
import re
import logging
import asyncio
import random

from utils.Chat import get_hash
from utils.bcolors import bcolors
from telethon import functions, errors, sync, types, utils
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
            if self.send_code_task == None or not self.is_verified or self.code != None or self.code_hash != None:  
                self.is_verified = True
                self.code = None
                self.codeHash = None
                
                ApiProcessor().set('phone', { 'id': self.id, 'isVerified': self.is_verified, 'code': self.code, 'codeHash': self.codeHash })                
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
            
            self.is_verified = False
            self.code = None
            
            ApiProcessor().set('phone', { 'id': self.id, 'isVerified': self.is_verified, 'code': self.code })
        else:
            self.is_verified = True
            self.code = None
            self.codeHash = None
            
            ApiProcessor().set('phone', { 'id': self.id, 'isVerified': self.is_verified, 'code': self.code, 'codeHash': self.codeHash })
    
    async def join(self, chat):
        """Вступает в чат

        Raises:
            Exception: Если ссылка не верна

        Returns:
            Chat: Телетоновский объект чата
        """
        channel, hash = get_hash(chat.link)
        
        if (channel == None and hash == None) or (channel != None and hash != None):
            raise Exception("Invalid chat link.")

        updates = await self.client(
            functions.channels.JoinChannelRequest(channel=channel) \
                if hash is None else functions.messages.ImportChatInviteRequest(hash=hash)
        )
        
        return updates.chats[0]
    
    async def invite(self, phone, chat):
        user = await phone.client.get_me()

        updates = await self.client(
            functions.channels.InviteToChannelRequest(
                channel=types.InputChannel(channel_id=chat.internal_id, access_hash=chat.access_hash), 
                users=[types.InputUser(user_id=user.id, access_hash=user.access_hash)]
            ) if chat.access_hash != None else 
                functions.messages.AddChatUserRequest(
                    chat_id=chat.internal_id, 
                    user_id=user.id, 
                    fwd_limit=100
                )
        )

        return updates.chats[0]
    
    async def is_participant(self, chat):
        """
        Проверяет является ли участником чата
        """
        if chat.internal_id != None:
            try:
                channel = utils.get_input_channel(
                    await self.client.get_input_entity(
                        types.InputChannel(channel_id=int(chat.internal_id), access_hash=int(chat.access_hash)) \
                            if chat.access_hash != None else types.InputChat(chat_id=int(chat.internal_id))
                    )
                )
                
                participant = utils.get_input_user(await self.client.get_me())
                
                await self.client(
                    functions.channels.GetParticipantRequest(
                        channel=channel,
                        participant=participant
                    )
                )
            except Exception as ex:
                print(f"{bcolors.FAIL}Chat or channel {self.id} doesn\'t available. Exception: {ex}.{bcolors.ENDC}")
                logging.error(f"Chat or channel {self.id} doesn\'t available. Exception: {ex}.")
            else:
                return True
        
        return False
    
    def get_chats_len(self):
        chats = ApiProcessor().get('chat', { 'phones': { 'id': self.id } })
        
        return len(chats)