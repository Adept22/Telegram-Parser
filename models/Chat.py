import re
import logging
import random
from telethon import functions, types

from threads.ChatThread import ChatThread
from core.PhonesManager import PhonesManager

class Chat:
    def __init__(self, dict):
        if dict is None:
            raise Exception('Unexpected chat dictionary')
            
        if not 'id' in dict or dict['id'] is None:
            raise Exception('Unexpected chat id')

        if not 'link' in dict or dict['link'] is None:
            raise Exception('Unexpected chat link')
        
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
    
    async def join(self, channel=None, hash=None):
        if channel is None and hash is None:
            return None

        updates = await phone.client(
            functions.channels.JoinChannelRequest(channel=channel) \
                if hash is None else functions.messages.ImportChatInviteRequest(hash=hash)
        )

        chat = updates.chats[0]

        return chat

    async def invite(chat):
        if not type(chat) == types.Chat or not type(chat) == types.Channel:
            return None
        
        user = await next_phone.client.get_me()

        time.sleep(random.randint(2, 5))

        updates = await phone.client(
            functions.channels.InviteToChannelRequest(channel=chat, user_id=user.id) \
                if type(chat) is types.Channel else 
                    functions.messages.AddChatUserRequest(chat_id=chat.id, user_id=user.id, fwd_limit=100)
        )

        chat = updates.chats[0]

        return chat
    
    def parse(self):
        print("Creating chat parsing thread...")
        logging.debug("Creating chat parsing thread...")
        chat_thread = ChatThread(id, )
        print("Starting chat parsing thread...")
        logging.debug("Starting chat parsing thread...")
        chat_thread.start()
    