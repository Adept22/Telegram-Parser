import asyncio
import re
import logging
import random
from telethon import functions, types

from utils.Chat import get_hash

from processors.ApiProcessor import ApiProcessor
from core.PhonesManager import PhonesManager
from threads.MembersParserThread import MembersParserThread
from threads.MessagesParserThread import MessagesParserThread
from models.Message import Message

class Chat:
    def __init__(self, dict):
        if dict is None:
            raise Exception('Unexpected chat dictionary')
            
        if not 'id' in dict or dict['id'] is None:
            raise Exception('Unexpected chat id')

        if not 'link' in dict or dict['link'] is None:
            raise Exception('Unexpected chat link')
        
        self.internal_id = None
        self.parsing_thread = None
        self._phones = []
        self.messages = []
        
        self.from_dict(dict)
    
    def from_dict(self, dict):
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        
        for key in dict:
            setattr(self, pattern.sub('_', key).lower(), dict[key])
            
        return self
    
    async def init(self):
        """
            TODO:
                - join to chat via link if internal_id is None
                - 
        """
        if self.is_available and self.internal_id == None:
            try:
                chat = await self.join()
            except:
                ApiProcessor().set('chat', { 'id': self.id, 'isAvailable': False })
            else:
                self.internal_id = chat.id
                self.access_hash = chat.access_hash
                
                ApiProcessor().set('chat', { 'id': self.id, 'isAvailable': True, 'internalId': self.internal_id, 'accessHash': self.access_hash })
                
                if len(self.phones) > 1:
                    try:
                        await self.invite()
                    except:
                        pass
        
        # messages = ApiProcessor.get('messages', { 'chat': { 'id': self.id } })
        
        # self.messages = [Message(message) for message in messages]
        
        return self
        
    @property
    def phones(self):
        return self._phones
    
    @phones.setter
    def phones(self, new_value):
        self._phones = []
        
        for phone in new_value:
            if phone['id'] in PhonesManager():
                self._phones.append(PhonesManager()[phone['id']])
    
    async def join(self):
        channel, hash = get_hash(self.link)
        
        if (channel == None and hash == None) or (channel != None and hash != None):
            raise Exception("Invalid chat link.")

        if len(self.phones) == 0:
            raise Exception("Doesn't exist available phone for joining.")

        updates = await self.phones[0].client(
            functions.channels.JoinChannelRequest(channel=channel) \
                if hash is None else functions.messages.ImportChatInviteRequest(hash=hash)
        )
        
        return updates.chats[0]

    async def invite(self):
        for phone in enumerate(self.phones, start=1):
            if len(self.phones) <= 1:
                raise Exception(f"Doesn't exist additional phones for inviting in chat {self.id}.")
            
            user = await phone.client.get_me()

            await self.phones[0].client(
                functions.channels.InviteToChannelRequest(
                    channel=types.InputChannel(channel_id=self.internal_id, access_hash=self.access_hash), 
                    user_id=user.id
                ) if self.access_hash != None else 
                    functions.messages.AddChatUserRequest(
                        chat_id=self.internal_id, 
                        user_id=user.id, 
                        fwd_limit=100
                    )
            )

            await asyncio.sleep(random.randint(2, 5))
    
    def parse(self):
        loop = asyncio.new_event_loop()
        
        #--> MEMBERS -->#
        if self.members_thread == None:
            self.members_thread = MembersParserThread(self, self.phones, loop)
            self.members_thread.start()
        else:
            print(f"Members parsing thread for chat {self.id} now is running.")
            logging.debug(f"Members parsing thread for chat {self.id} now is running.")
        #--< MEMBERS --<#
        
        #--> MESSAGES -->#
        if self.messages_thread == None:
            self.messages_thread = MessagesParserThread(self, self.phones, loop)
            self.messages_thread.start()
        else:
            print(f"Messages parsing thread for chat {self.id} now is running.")
            logging.debug(f"Messages parsing thread for chat {self.id} now is running.")
        #--< MESSAGES --<#
    